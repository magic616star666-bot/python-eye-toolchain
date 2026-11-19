package com.veercreation.pyeye.kotlincheck

import android.app.Activity
import android.os.Bundle
import android.widget.TextView

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(TextView(this).apply {
            text = "Python Eye Kotlin APK compiled"
            textSize = 22f
        })
    }
}
