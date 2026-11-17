package com.veercreation.pyeye.smoketest;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

public class MainActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        TextView text = new TextView(this);
        text.setTextSize(22);
        text.setPadding(36, 90, 36, 36);
        setContentView(text);
        try {
            if (!Python.isStarted()) {
                Python.start(new AndroidPlatform(this));
            }
            String result = Python.getInstance().getModule("hello")
                .callAttr("greet", 3).toString();
            text.setText(result);
        } catch (Exception error) {
            text.setText("APK started, but Python failed:\n" + error);
        }
    }
}
