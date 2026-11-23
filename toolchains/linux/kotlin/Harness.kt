// CI harness: runs the IDE's own pure-JVM Linux core (LinuxCore.kt, copied
// byte-for-byte from the Python Eye IDE source) on the GitHub runner.
import com.pydroid.studio.linux.LinuxLayout
import com.pydroid.studio.linux.ProotCommand
import com.pydroid.studio.linux.RootfsExtractor
import com.pydroid.studio.linux.RootfsSetup
import java.io.File
import kotlin.system.exitProcess

fun main(args: Array<String>) {
    try {
        when (args.getOrNull(0)) {
            // extract <tar file or -> <into dir> <strip components>
            "extract" -> {
                val input = if (args[1] == "-") System.`in` else File(args[1]).inputStream()
                val stats = input.buffered(1 shl 20).use { RootfsExtractor.extract(it, File(args[2]), args[3].toInt()) }
                println("EXTRACT_OK $stats")
            }
            // configure <rootfs dir> <fake proc dir>
            "configure" -> {
                RootfsSetup.configure(File(args[1]))
                RootfsSetup.writeFakeProc(File(args[2]))
                println("CONFIGURE_OK")
            }
            // command <runtime base on the DEVICE> <guest cwd> <host projects dir> <args out> <env out>
            "command" -> {
                val layout = LinuxLayout(File(args[1]))
                val a = ProotCommand.args(layout, args[2], "__PYEYE_CMD__", listOf(args[3] to "/root/projects"), fakeProc = true)
                File(args[4]).writeText(a.joinToString("\n", postfix = "\n"))
                File(args[5]).writeText(
                    ProotCommand.environment(layout).entries.joinToString("\n", postfix = "\n") { "${it.key}=${it.value}" }
                )
                println("COMMAND_OK ${a.size} args")
                println(a.joinToString(" ") { ProotCommand.shellQuote(it) })
            }
            else -> {
                System.err.println("usage: extract|configure|command …")
                exitProcess(2)
            }
        }
    } catch (e: Exception) {
        System.err.println("HARNESS_FAILED ${e.javaClass.simpleName}: ${e.message}")
        exitProcess(1)
    }
}
