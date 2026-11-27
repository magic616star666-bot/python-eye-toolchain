package com.veer.build;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.util.*;

/** Python Eye Android native build preflight; does not change SDK licenses. */
public final class NativeSdkPreflight {
    private static final String REV = "1a028f5a3972b67dd8d8752f882113d475e7ec4c";
    private static final String BASE = "https://huggingface.co/Cactus-Compute/cactus/resolve/" + REV + "/releases/4.0.0/android-arm64/";
    private static final String LIB_SHA = "4f75e975f6a859979a2715a89fdbc0fc32742cde001f8674598cf89017d39fdf";
    private static final String MODULE_BLOB = "73aa2b4f9383421f61a02a9755d96cdc4e391f0c";
    private static final String MODULE = "\nset(_compiler_id_version_compute \"\n  /* __IBMCPP__ = VRP */\n# define @PREFIX@COMPILER_VERSION_MAJOR @MACRO_DEC@(__IBMCPP__/100)\n# define @PREFIX@COMPILER_VERSION_MINOR @MACRO_DEC@(__IBMCPP__/10 % 10)\n# define @PREFIX@COMPILER_VERSION_PATCH @MACRO_DEC@(__IBMCPP__    % 10)\")\n";
    private NativeSdkPreflight() {}
    private static String hex(byte[] data) { return HexFormat.of().formatHex(data); }
    static String sha(Path path) throws Exception {
        MessageDigest d = MessageDigest.getInstance("SHA-256");
        try (InputStream in = Files.newInputStream(path)) { byte[] b = new byte[65536]; for(int n; (n=in.read(b))!=-1;) d.update(b,0,n); }
        return hex(d.digest());
    }
    static String blob(byte[] b) throws Exception {
        MessageDigest d=MessageDigest.getInstance("SHA-1");
        d.update(("blob "+b.length+"\0").getBytes(StandardCharsets.UTF_8)); return hex(d.digest(b));
    }
    private static void replace(Path tmp, Path dest) throws IOException {
        try { Files.move(tmp,dest,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING); }
        catch(AtomicMoveNotSupportedException ex) { Files.move(tmp,dest,StandardCopyOption.REPLACE_EXISTING); }
    }
    public static boolean repairCmake(Path root, String version) throws Exception {
        if(root==null || !"3.22.1".equals(version)) return false;
        Path dir=root.resolve("share/cmake-3.22/Modules/Compiler");
        if(!Files.isDirectory(dir) || !Files.isRegularFile(dir.resolve("VisualAge-CXX-DetermineCompiler.cmake"))) throw new IOException("Incomplete CMake 3.22.1 modules directory: "+dir);
        Path target=dir.resolve("IBMCPP-CXX-DetermineVersionInternal.cmake");
        if(Files.isRegularFile(target) && Files.size(target)>0) return false;
        byte[] original=MODULE.getBytes(StandardCharsets.UTF_8);
        if(!MODULE_BLOB.equals(blob(original))) throw new IOException("CMake repair payload identity mismatch");
        Path tmp=Files.createTempFile(dir,".cmake-module-",".part");
        try { Files.write(tmp,original); replace(tmp,target); } finally { Files.deleteIfExists(tmp); }
        return true;
    }
    private static boolean header(Path p) throws IOException {
        if(!Files.isRegularFile(p) || Files.size(p)==0 || Files.size(p)>1024*1024) return false;
        String s=Files.readString(p); for(String x:new String[]{"cactus_load","cactus_describe","cactus_complete","cactus_transcribe","cactus_models"}) if(!s.contains(x)) return false;
        return !s.contains("<!DOCTYPE html") && !s.startsWith("version https://git-lfs");
    }
    private static boolean library(Path p) throws Exception { return Files.isRegularFile(p) && LIB_SHA.equals(sha(p)); }
    private static void download(String name,Path dest,long max) throws Exception {
        URL u=new URI(BASE+name).toURL(); Path tmp=Files.createTempFile(dest.getParent(),".cactus-",".part");
        try {
            for(int redirects=0; redirects<10; redirects++) {
                if(!"https".equalsIgnoreCase(u.getProtocol())) throw new IOException("HTTPS required for Cactus SDK");
                HttpURLConnection c=(HttpURLConnection)u.openConnection();
                c.setInstanceFollowRedirects(false); c.setConnectTimeout(30000); c.setReadTimeout(120000); c.setRequestProperty("User-Agent","PythonEye-NativeSDK/1.0");
                try {
                    int status=c.getResponseCode();
                    if(status>=300 && status<400) { String location=c.getHeaderField("Location"); if(location==null) throw new IOException("Missing redirect"); u=new URL(u,location); continue; }
                    if(status!=200) throw new IOException("Cactus "+name+" HTTP "+status);
                    if(c.getContentLengthLong()>max) throw new IOException("Cactus download too large");
                    try(InputStream in=c.getInputStream(); OutputStream out=Files.newOutputStream(tmp)) { byte[] b=new byte[65536]; long total=0; for(int n;(n=in.read(b))!=-1;) { total+=n; if(total>max) throw new IOException("Cactus download too large"); out.write(b,0,n); } }
                    if(name.equals("libcactus.a") ? !library(tmp) : !header(tmp)) throw new IOException("Invalid Cactus SDK file: "+name);
                    replace(tmp,dest); return;
                } finally { c.disconnect(); }
            }
            throw new IOException("Too many Cactus HTTPS redirects");
        } finally { Files.deleteIfExists(tmp); }
    }
    private static void copy(Path from,Path to) throws IOException {
        Path tmp=Files.createTempFile(to.getParent(),".sdk-copy-",".part");
        try { Files.copy(from,tmp,StandardCopyOption.REPLACE_EXISTING); replace(tmp,to); } finally { Files.deleteIfExists(tmp); }
    }
    /** Cache SDK once; materialize into a project's existing native vendor directory. */
    public static void prepareCactus(Path cache,Path vendor,boolean offline) throws Exception {
        Files.createDirectories(cache); Files.createDirectories(vendor);
        for(String name:new String[]{"libcactus.a","cactus.h"}) {
            boolean lib=name.equals("libcactus.a"); Path local=vendor.resolve(name), shared=cache.resolve(name);
            if(lib?library(local):header(local)) continue;
            if(!(lib?library(shared):header(shared))) {
                if(offline) throw new IOException("Missing Cactus 4.0.0 "+name+" in cache: "+cache);
                download(name,shared,lib?512L*1024*1024:1024*1024);
            }
            copy(shared,local);
        }
        if(!library(vendor.resolve("libcactus.a")) || !header(vendor.resolve("cactus.h"))) throw new IOException("Cactus SDK validation failed");
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=5) throw new IllegalArgumentException("Usage: NativeSdkPreflight <cmake-root-or-dash> <cmake-version> <shared-cache> <project-vendor-dir> <offline:true|false>");
        if(!args[0].equals("-") && repairCmake(Path.of(args[0]),args[1])) System.out.println("Restored original CMake 3.22.1 compiler module");
        prepareCactus(Path.of(args[2]),Path.of(args[3]),Boolean.parseBoolean(args[4]));
        System.out.println("Cactus SDK files prepared; native linking not tested");
    }
}
