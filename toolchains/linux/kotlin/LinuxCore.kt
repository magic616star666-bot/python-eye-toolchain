package com.pydroid.studio.linux

import java.io.ByteArrayOutputStream
import java.io.File
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.nio.file.Files
import java.nio.file.Paths
import java.nio.file.StandardCopyOption

/*
 * Pure-JVM core of the Python Eye Linux runtime (PRoot + Ubuntu rootfs).
 * No Android imports: the SAME file is compiled and executed by the
 * python-eye-toolchain GitHub CI (toolchains/linux/kotlin), so what CI tests is
 * exactly what the phone runs. Keep both copies identical.
 */

/** Folder layout of the runtime inside app-private storage. */
class LinuxLayout(val base: File) {
    /** proot bundle: bin/proot, lib/libtalloc.so.2, libexec/proot/loader(32). */
    val prootDir = File(base, "proot")
    val proot = File(prootDir, "bin/proot")
    val loader = File(prootDir, "libexec/proot/loader")
    val loader32 = File(prootDir, "libexec/proot/loader32")
    val libDir = File(prootDir, "lib")
    val rootfs = File(base, "ubuntu")
    val tmp = File(base, "tmp")
    val fakeProc = File(base, "proc-fake")
    /** Written last, after a fully successful install + boot test. */
    val marker = File(base, "runtime-ready.json")
    val downloads = File(base, "downloads")

    fun prootPresent(): Boolean = proot.isFile && loader.isFile
    fun rootfsPresent(): Boolean = File(rootfs, "usr/bin/env").exists() && File(rootfs, "etc/os-release").exists()
    fun ready(): Boolean = prootPresent() && rootfsPresent() && marker.isFile
}

/**
 * Unpacks a Linux rootfs tar stream (already decompressed) for use with PRoot.
 * Unlike a tool archive, a rootfs legitimately contains ABSOLUTE symlinks
 * (/etc/alternatives/…); they are stored verbatim and only ever interpreted
 * inside the guest by PRoot. Host-side safety comes from never following a
 * symlink while writing: every parent directory is resolved with guest
 * semantics, clamped to the rootfs, so no entry can escape [into].
 * Hard links become absolute guest symlinks (Android app storage forbids link()).
 * Device nodes and FIFOs are skipped (PRoot binds the host /dev).
 */
object RootfsExtractor {
    class Stats {
        var files = 0
        var dirs = 0
        var symlinks = 0
        var hardlinks = 0
        var skipped = 0
        var bytes = 0L
        override fun toString() = "files=$files dirs=$dirs symlinks=$symlinks hardlinks=$hardlinks skipped=$skipped bytes=$bytes"
    }

    fun extract(
        input: InputStream,
        into: File,
        stripComponents: Int,
        maxBytes: Long = 12L * 1024 * 1024 * 1024,
        progress: (Long) -> Unit = {},
        cancelled: () -> Boolean = { false },
    ): Stats {
        into.mkdirs()
        val base = into.canonicalFile
        val stats = Stats()
        val header = ByteArray(512)
        var longName: String? = null
        var longLink: String? = null
        var pax = emptyMap<String, String>()
        val hardLinks = mutableListOf<Pair<List<String>, List<String>>>()
        var entries = 0
        while (true) {
            if (cancelled()) throw IOException("Rootfs extraction cancelled")
            if (!readBlock(input, header)) break
            if (header.all { it == 0.toByte() }) break
            if (++entries > 600_000) throw IOException("Rootfs has too many entries")
            val size = numeric(header, 124, 12)
            if (size < 0L || size > 8L * 1024 * 1024 * 1024) throw IOException("Invalid tar member size")
            val padded = (size + 511) / 512 * 512
            val type = header[156].toInt().toChar()
            val mode = numeric(header, 100, 8).toInt()
            val rawName = pax["path"] ?: longName ?: (cString(header, 0, 100).let { n ->
                val p = ustarPrefix(header)
                if (p.isEmpty()) n else "$p/$n"
            })
            val rawLink = pax["linkpath"] ?: longLink ?: cString(header, 157, 100)
            when (type) {
                'L' -> { longName = readString(input, size, padded); continue }
                'K' -> { longLink = readString(input, size, padded); continue }
                'x' -> {
                    if (size > 1_048_576L) throw IOException("PAX header too large")
                    pax = parsePax(readBytes(input, size)); skip(input, padded - size); continue
                }
                'g' -> { skip(input, padded); continue }
            }
            val parts = guestParts(rawName).drop(stripComponents)
            if (parts.isEmpty()) {
                skip(input, padded)
                longName = null; longLink = null; pax = emptyMap()
                continue
            }
            val parent = resolveDir(base, parts.dropLast(1))
            val target = File(parent, parts.last())
            when (type) {
                '5' -> {
                    val p = target.toPath()
                    if (Files.isSymbolicLink(p)) {
                        // Keep an existing guest symlink (e.g. bin -> usr/bin).
                    } else if (!target.isDirectory) {
                        if (target.exists()) Files.delete(p)
                        if (!target.mkdirs() && !target.isDirectory) throw IOException("Cannot create dir ${parts.joinToString("/")}")
                    }
                    stats.dirs++
                    skip(input, padded)
                }
                '0', '\u0000', '7' -> {
                    if (size > maxBytes - stats.bytes) throw IOException("Rootfs is larger than allowed")
                    val p = target.toPath()
                    if (Files.isSymbolicLink(p) || target.isFile) Files.delete(p)
                    else if (target.isDirectory) throw IOException("File replaces directory: ${parts.joinToString("/")}")
                    target.outputStream().use { out ->
                        copy(input, out, size) { n ->
                            if (cancelled()) throw IOException("Rootfs extraction cancelled")
                            stats.bytes += n
                            progress(stats.bytes)
                        }
                    }
                    skip(input, padded - size)
                    applyMode(target, mode)
                    stats.files++
                }
                '2' -> {
                    if (rawLink.isEmpty() || rawLink.length > 4096 || rawLink.contains('\u0000'))
                        throw IOException("Invalid symlink target: ${parts.joinToString("/")}")
                    val p = target.toPath()
                    if (Files.isSymbolicLink(p) || target.isFile) Files.delete(p)
                    else if (target.isDirectory) deleteTree(target)
                    Files.createSymbolicLink(p, Paths.get(rawLink))
                    stats.symlinks++
                    skip(input, padded)
                }
                '1' -> {
                    val source = guestParts(rawLink).drop(stripComponents)
                    if (source.isEmpty()) throw IOException("Invalid hard link: ${parts.joinToString("/")}")
                    hardLinks.add(parts to source)
                    skip(input, padded)
                }
                else -> { // '3','4','6' devices / FIFOs, 'S' sparse … never materialised
                    stats.skipped++
                    skip(input, padded)
                }
            }
            longName = null; longLink = null; pax = emptyMap()
        }
        for ((linkParts, sourceParts) in hardLinks) {
            val parent = resolveDir(base, linkParts.dropLast(1))
            val target = File(parent, linkParts.last())
            val p = target.toPath()
            if (Files.isSymbolicLink(p) || target.isFile) Files.delete(p)
            Files.createSymbolicLink(p, Paths.get("/" + sourceParts.joinToString("/")))
            stats.hardlinks++
        }
        return stats
    }

    /** Splits an archive path into safe guest components. ".." is refused. */
    internal fun guestParts(name: String): List<String> {
        if (name.length > 8192 || name.contains('\u0000')) throw IOException("Archive path is too long")
        val parts = name.split('/').filter { it.isNotEmpty() && it != "." }
        if (parts.any { it == ".." }) throw IOException("Archive path leaves the rootfs: $name")
        return parts
    }

    /**
     * Real host directory for guest path [guest], creating missing directories.
     * Symlinks met on the way are followed with GUEST semantics (absolute
     * targets start at the rootfs, ".." never goes above it).
     */
    internal fun resolveDir(base: File, guest: List<String>, depth: Int = 0): File {
        if (depth > 40) throw IOException("Too many symlink levels in rootfs")
        var current = base
        val done = ArrayList<String>()
        for ((index, part) in guest.withIndex()) {
            val next = File(current, part)
            val path = next.toPath()
            if (Files.isSymbolicLink(path)) {
                val link = Files.readSymbolicLink(path).toString()
                val rebuilt = ArrayList<String>()
                if (!link.startsWith("/")) rebuilt.addAll(done)
                for (piece in link.split('/')) {
                    when (piece) {
                        "", "." -> Unit
                        ".." -> if (rebuilt.isNotEmpty()) rebuilt.removeAt(rebuilt.lastIndex)
                        else -> rebuilt.add(piece)
                    }
                }
                rebuilt.addAll(guest.subList(index + 1, guest.size))
                return resolveDir(base, rebuilt, depth + 1)
            }
            if (!next.exists()) {
                if (!next.mkdirs() && !next.isDirectory) throw IOException("Cannot create ${done.joinToString("/")}/$part")
            } else if (!next.isDirectory) {
                throw IOException("Not a directory inside rootfs: ${done.joinToString("/")}/$part")
            }
            current = next
            done.add(part)
        }
        return current
    }

    private fun applyMode(file: File, mode: Int) {
        file.setReadable(true, false)
        file.setWritable(true, true)
        if (mode and 0b001_001_001 != 0) file.setExecutable(true, false)
    }

    private fun deleteTree(dir: File) {
        Files.walk(dir.toPath()).use { stream ->
            stream.sorted(Comparator.reverseOrder()).forEach { Files.deleteIfExists(it) }
        }
    }

    private fun parsePax(bytes: ByteArray): Map<String, String> {
        val result = mutableMapOf<String, String>()
        var pos = 0
        while (pos < bytes.size) {
            var space = pos
            while (space < bytes.size && bytes[space] != ' '.code.toByte()) space++
            if (space >= bytes.size || space - pos > 12) throw IOException("Invalid PAX length")
            val count = String(bytes, pos, space - pos, Charsets.US_ASCII).toIntOrNull() ?: throw IOException("Invalid PAX record")
            if (count <= space - pos + 1 || count > bytes.size - pos) throw IOException("PAX record exceeds header")
            val record = String(bytes, space + 1, count - (space - pos) - 1, Charsets.UTF_8).trimEnd('\n')
            val eq = record.indexOf('=')
            if (eq > 0) {
                val key = record.substring(0, eq)
                if (key == "path" || key == "linkpath") result[key] = record.substring(eq + 1)
            }
            pos += count
        }
        return result
    }

    private fun ustarPrefix(h: ByteArray): String =
        if (String(h, 257, 5, Charsets.US_ASCII) == "ustar") cString(h, 345, 155) else ""

    private fun cString(b: ByteArray, off: Int, len: Int): String {
        var end = off
        while (end < off + len && b[end] != 0.toByte()) end++
        return String(b, off, end - off, Charsets.UTF_8)
    }

    /** Octal field, or GNU base-256 for large values. */
    private fun numeric(b: ByteArray, off: Int, len: Int): Long {
        if ((b[off].toInt() and 0x80) != 0) {
            var v = 0L
            for (i in off + 1 until off + len) v = (v shl 8) or (b[i].toLong() and 0xff)
            return v
        }
        val s = cString(b, off, len).trim()
        return if (s.isEmpty()) 0L else s.toLong(8)
    }

    private fun readBlock(input: InputStream, buf: ByteArray): Boolean {
        var n = 0
        while (n < buf.size) {
            val r = input.read(buf, n, buf.size - n)
            if (r < 0) {
                if (n == 0) return false
                throw IOException("Rootfs archive ends too early")
            }
            n += r
        }
        return true
    }

    private fun readString(input: InputStream, size: Long, padded: Long): String {
        if (size > 16_384L) throw IOException("Tar long name too large")
        val text = String(readBytes(input, size), Charsets.UTF_8).trimEnd('\u0000')
        skip(input, padded - size)
        return text
    }

    private fun readBytes(input: InputStream, size: Long): ByteArray {
        val out = ByteArrayOutputStream()
        copy(input, out, size)
        return out.toByteArray()
    }

    private fun copy(input: InputStream, out: OutputStream, size: Long, onChunk: (Long) -> Unit = {}) {
        var left = size
        val buf = ByteArray(64 * 1024)
        while (left > 0) {
            val r = input.read(buf, 0, minOf(buf.size.toLong(), left).toInt())
            if (r < 0) throw IOException("Rootfs archive ends too early")
            if (r == 0) continue
            out.write(buf, 0, r)
            onChunk(r.toLong())
            left -= r
        }
    }

    private fun skip(input: InputStream, count: Long) {
        var left = count
        val buf = ByteArray(16_384)
        while (left > 0) {
            val r = input.read(buf, 0, minOf(buf.size.toLong(), left).toInt())
            if (r < 0) throw IOException("Rootfs archive ends too early")
            left -= r
        }
    }
}

/** First-boot configuration written into the rootfs (no network needed). */
object RootfsSetup {
    /** Fake /proc files for Android 8+, where apps may not read the real ones. */
    val FAKE_PROC: List<Pair<String, String>> = listOf(
        "loadavg" to "/proc/loadavg",
        "stat" to "/proc/stat",
        "uptime" to "/proc/uptime",
        "version" to "/proc/version",
        "vmstat" to "/proc/vmstat",
        "cap_last_cap" to "/proc/sys/kernel/cap_last_cap",
        "max_user_watches" to "/proc/sys/fs/inotify/max_user_watches",
    )

    fun configure(rootfs: File, hostName: String = "python-eye") {
        writeGuest(rootfs, "etc/resolv.conf", "nameserver 8.8.8.8\nnameserver 1.1.1.1\nnameserver 8.8.4.4\n")
        writeGuest(rootfs, "etc/hosts", "127.0.0.1   localhost\n127.0.1.1   $hostName\n::1         localhost ip6-localhost ip6-loopback\n")
        writeGuest(rootfs, "etc/hostname", "$hostName\n")
        // apt drops privileges to _apt, which PRoot's fake root cannot do on Android.
        writeGuest(rootfs, "etc/apt/apt.conf.d/99python-eye",
            "APT::Sandbox::User \"root\";\nAcquire::Retries \"3\";\nAPT::Install-Recommends \"false\";\nDpkg::Use-Pty \"0\";\n")
        // Never try to start services inside the container.
        writeGuest(rootfs, "usr/sbin/policy-rc.d", "#!/bin/sh\nexit 101\n", executable = true)
        writeGuest(rootfs, "etc/profile.d/python-eye.sh",
            "export LANG=C.UTF-8\nexport PIP_ROOT_USER_ACTION=ignore\nexport npm_config_update_notifier=false\nexport npm_config_fund=false\n")
        for (dir in listOf("tmp", "root", "root/projects", "var/tmp", "dev/shm")) {
            RootfsExtractor.resolveDir(rootfs.canonicalFile, dir.split('/'))
        }
        File(rootfs, "tmp").setWritable(true, false)
    }

    fun writeFakeProc(dir: File) {
        dir.mkdirs()
        val cpu = "cpu  1957 0 2877 93280 262 342 254 87 0 0\n" +
            (0 until 8).joinToString("") { "cpu$it 245 0 360 11660 33 43 32 11 0 0\n" } +
            "intr 63361 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0\nctxt 38014093\nbtime 1694292441\n" +
            "processes 26442\nprocs_running 1\nprocs_blocked 0\nsoftirq 75663 0 5903 6 25375 10774 0 243 11685 0 21677\n"
        val files = mapOf(
            "loadavg" to "0.12 0.07 0.02 2/165 765\n",
            "stat" to cpu,
            "uptime" to "124.08 932.80\n",
            "version" to "Linux version 6.2.1-python-eye (python-eye@localhost) (gcc version 13.2.0) #1 SMP PREEMPT_DYNAMIC\n",
            "vmstat" to listOf("nr_free_pages 136757", "nr_zone_inactive_anon 0", "nr_zone_active_anon 0",
                "nr_zone_inactive_file 0", "nr_zone_active_file 0", "nr_mlock 0", "nr_bounce 0",
                "nr_dirtied 0", "nr_written 0", "pgpgin 0", "pgpgout 0", "pswpin 0", "pswpout 0",
                "pgfault 0", "pgmajfault 0").joinToString("\n", postfix = "\n"),
            "cap_last_cap" to "40\n",
            "max_user_watches" to "4096\n",
        )
        for ((name, text) in files) File(dir, name).writeText(text)
    }

    /** Writes a file at a guest path without following a host symlink at its place. */
    private fun writeGuest(rootfs: File, guest: String, text: String, executable: Boolean = false) {
        val parts = guest.split('/')
        val parent = RootfsExtractor.resolveDir(rootfs.canonicalFile, parts.dropLast(1))
        val target = File(parent, parts.last())
        Files.deleteIfExists(target.toPath())
        val tmp = File(parent, ".${parts.last()}.pyeye-tmp")
        tmp.writeText(text)
        Files.move(tmp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING)
        target.setReadable(true, false)
        if (executable) target.setExecutable(true, false)
    }
}

/** Builds the exact PRoot command line used by the terminal, installers and CI. */
object ProotCommand {
    const val GUEST_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

    /**
     * @param binds host directory -> guest path, e.g. the projects folder -> /root/projects.
     * @param fakeProc bind the fake /proc files (Android 8+ hides the real ones from apps).
     */
    fun args(
        layout: LinuxLayout,
        guestCwd: String,
        shellCommand: String,
        binds: List<Pair<String, String>> = emptyList(),
        fakeProc: Boolean = true,
        login: Boolean = true,
    ): List<String> {
        val rootfs = layout.rootfs.absolutePath
        val a = mutableListOf(
            layout.proot.absolutePath,
            "--kill-on-exit",
            "--link2symlink",
            "--root-id",
            "--sysvipc",
            "--rootfs=$rootfs",
            "--cwd=$guestCwd",
            "--bind=/dev",
            "--bind=/dev/urandom:/dev/random",
            "--bind=/proc",
            "--bind=/proc/self/fd:/dev/fd",
            "--bind=/proc/self/fd/0:/dev/stdin",
            "--bind=/proc/self/fd/1:/dev/stdout",
            "--bind=/proc/self/fd/2:/dev/stderr",
            "--bind=/sys",
            "--bind=$rootfs/tmp:/dev/shm",
        )
        if (fakeProc) {
            for ((name, guest) in RootfsSetup.FAKE_PROC) a += "--bind=${File(layout.fakeProc, name).absolutePath}:$guest"
        }
        for ((host, guest) in binds) a += "--bind=$host:$guest"
        a += listOf(
            "/usr/bin/env", "-i",
            "HOME=/root", "USER=root", "LOGNAME=root", "SHELL=/bin/bash",
            "LANG=C.UTF-8", "TERM=dumb", "NO_COLOR=1",
            "PATH=$GUEST_PATH", "TMPDIR=/tmp",
            "DEBIAN_FRONTEND=noninteractive", "APT_LISTCHANGES_FRONTEND=none",
            "PIP_ROOT_USER_ACTION=ignore", "PYTHONUNBUFFERED=1",
            "npm_config_update_notifier=false", "npm_config_fund=false", "npm_config_audit=false",
            "/bin/bash", if (login) "-lc" else "-c", shellCommand,
        )
        return a
    }

    /** Host environment PRoot itself needs (loader, tmp, bundled libtalloc). */
    fun environment(layout: LinuxLayout, noSeccomp: Boolean = false): Map<String, String> {
        val env = linkedMapOf(
            "PROOT_TMP_DIR" to layout.tmp.absolutePath,
            "PROOT_LOADER" to layout.loader.absolutePath,
            "LD_LIBRARY_PATH" to layout.libDir.absolutePath,
        )
        if (layout.loader32.isFile) env["PROOT_LOADER_32"] = layout.loader32.absolutePath
        if (noSeccomp) env["PROOT_NO_SECCOMP"] = "1"
        return env
    }

    fun shellQuote(arg: String): String =
        if (arg.isNotEmpty() && arg.all { it.isLetterOrDigit() || it in "-_./=:,+@%" }) arg
        else "'" + arg.replace("'", "'\"'\"'") + "'"
}
