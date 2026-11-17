plugins {
    id("com.android.application")
    id("com.chaquo.python")
}

android {
    namespace = "com.veercreation.pyeye.smoketest"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.veercreation.pyeye.smoketest"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
        ndk {
            abiFilters += listOf("arm64-v8a")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

chaquopy {
    defaultConfig {
        version = "3.10"
    }
}
