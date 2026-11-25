import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/** Reproduces exactly what Android Lint's IntelliJ core does, plus image I/O, headless. */
public class AwtLintProbe {
    public static void main(String[] args) throws Exception {
        System.out.println("java.home=" + System.getProperty("java.home"));
        System.out.println("java.io.tmpdir=" + System.getProperty("java.io.tmpdir"));
        System.out.println("headless=" + java.awt.GraphicsEnvironment.isHeadless());
        // 1) lint path: SwingUtilities.invokeLater -> EventQueue -> Toolkit static init -> libawt
        final boolean[] ran = {false};
        javax.swing.SwingUtilities.invokeAndWait(() -> ran[0] = true);
        if (!ran[0]) throw new IllegalStateException("EDT task did not run");
        System.out.println("SWING_EDT_OK toolkit=" + java.awt.Toolkit.getDefaultToolkit().getClass().getName());
        // 2) image I/O (lint reads PNG/JPEG resources)
        java.awt.image.BufferedImage img = new java.awt.image.BufferedImage(16, 16, java.awt.image.BufferedImage.TYPE_INT_ARGB);
        img.setRGB(3, 3, 0xff3ecf8e);
        File png = new File(args[0], "probe.png");
        File jpg = new File(args[0], "probe.jpg");
        if (!javax.imageio.ImageIO.write(img, "png", png)) throw new IllegalStateException("png");
        java.awt.image.BufferedImage rgb = new java.awt.image.BufferedImage(16, 16, java.awt.image.BufferedImage.TYPE_INT_RGB);
        if (!javax.imageio.ImageIO.write(rgb, "jpg", jpg)) throw new IllegalStateException("jpg");
        if (javax.imageio.ImageIO.read(png).getRGB(3, 3) != 0xff3ecf8e) throw new IllegalStateException("png readback");
        System.out.println("IMAGEIO_OK png=" + png.length() + " jpg=" + jpg.length());
        // 3) color management + fonts (lcms, fontmanager) used by some lint image checks
        java.awt.color.ICC_Profile.getInstance(java.awt.color.ColorSpace.CS_sRGB).getData();
        System.out.println("LCMS_OK");
        // 4) every native library must come from this JDK or Android itself, never Termux
        List<String> bad = new ArrayList<>();
        String jdk = new File(System.getProperty("java.home")).getCanonicalPath();
        for (String line : Files.readAllLines(Path.of("/proc/self/maps"))) {
            int i = line.indexOf('/');
            if (i < 0 || !line.endsWith(".so")) continue;
            String lib = line.substring(i);
            if (lib.contains("/com.termux/files/usr/")) bad.add(lib);
            else if (lib.contains("/lib") && (lib.startsWith(jdk) || lib.startsWith("/system/") || lib.startsWith("/apex/") || lib.startsWith("/vendor/")))
                continue;
        }
        if (!bad.isEmpty()) throw new IllegalStateException("Loaded from Termux prefix (not relocatable): " + bad);
        System.out.println("RELOCATABLE_OK (no library loaded from the Termux prefix)");
        System.out.println("AWT_LINT_PROBE_PASS");
    }
}
