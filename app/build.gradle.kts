plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp")
}

android {
    namespace = "com.mrpeel.cricketbattingtracker"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.mrpeel.cricketbattingtracker"
        minSdk = 33
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        externalNativeBuild {
            cmake {
                arguments("-DANDROID_STL=c++_static")
            }
        }
    }

    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt")
            version = "3.22.1"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            isDebuggable = true
            signingConfig = signingConfigs.getByName("debug")
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
        debug {
            isMinifyEnabled = false
            isDebuggable = true
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
    }
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.8"
    }
    packaging {
        jniLibs {
            useLegacyPackaging = false
        }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")
    implementation("androidx.activity:activity-compose:1.8.2")
    implementation("androidx.fragment:fragment-ktx:1.6.2")
    implementation(platform("androidx.compose:compose-bom:2024.02.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("com.google.android.gms:play-services-wearable:18.1.0")
    
    // Room
    val roomVersion = "2.6.1"
    implementation("androidx.room:room-runtime:$roomVersion")
    implementation("androidx.room:room-ktx:$roomVersion")
    ksp("androidx.room:room-compiler:$roomVersion")

    // Health Connect
    implementation("androidx.health.connect:connect-client:1.1.0-alpha07")

    // CameraX — video recording (1.4.1+ for 16 KB alignment support)
    val cameraxVersion = "1.4.1"
    implementation("androidx.camera:camera-core:$cameraxVersion")
    implementation("androidx.camera:camera-camera2:$cameraxVersion")
    implementation("androidx.camera:camera-lifecycle:$cameraxVersion")
    implementation("androidx.camera:camera-video:$cameraxVersion")
    implementation("androidx.camera:camera-view:$cameraxVersion")
    
    // Resolve CameraX ListenableFuture classpath compilation errors
    implementation("com.google.guava:guava:31.1-android")

    // Polar BLE SDK — bottom hand sensor (Polar Verity Sense)
    implementation("com.github.polarofficial:polar-ble-sdk:5.5.0")
    implementation("io.reactivex.rxjava3:rxjava:3.1.9")
    implementation("io.reactivex.rxjava3:rxandroid:3.0.2")

    // DataStore — persist Polar device pairing
    implementation("androidx.datastore:datastore-preferences:1.0.0")

    // ONNX Runtime Android SDK — Hardware-accelerated TCN model inference (1.22.0 for 16 KB page alignment)
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.22.0")

    testImplementation("junit:junit:4.13.2")
    testImplementation("com.microsoft.onnxruntime:onnxruntime:1.22.0")
}

// Automatically enforce 16 KB (16384 bytes) Zip offset alignment & re-signing on packaged APK outputs
androidComponents {
    onVariants { variant ->
        val variantName = variant.name.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
        val zipAlignTask = tasks.register("zipAlign16kb$variantName") {
            doLast {
                val apkDir = file("${layout.buildDirectory.get()}/outputs/apk/${variant.name}")
                val sdkDir = android.sdkDirectory
                val buildToolsVer = android.buildToolsVersion
                val zipalignExe = "$sdkDir/build-tools/$buildToolsVer/zipalign"
                val apksignerExe = "$sdkDir/build-tools/$buildToolsVer/apksigner"
                val keystore = file("${System.getProperty("user.home")}/.android/debug.keystore")

                apkDir.listFiles()?.filter { it.name.endsWith(".apk") && !it.name.startsWith("16kb-aligned-") }?.forEach { apkFile ->
                    val tempAligned = file("${apkFile.parent}/16kb-aligned-${apkFile.name}")
                    println("📦 Post-processing 16 KB Zip alignment for ${apkFile.name}...")
                    exec {
                        commandLine(zipalignExe, "-f", "16384", apkFile.absolutePath, tempAligned.absolutePath)
                    }
                    if (keystore.exists()) {
                        exec {
                            commandLine(apksignerExe, "sign", "--ks", keystore.absolutePath, "--ks-pass", "pass:android", "--key-pass", "pass:android", tempAligned.absolutePath)
                        }
                    }
                    tempAligned.copyTo(apkFile, overwrite = true)
                    tempAligned.delete()
                    println("✅ Successfully 16 KB zip-aligned and re-signed ${apkFile.name}")
                }
            }
        }
        tasks.findByName("package$variantName")?.finalizedBy(zipAlignTask)
    }
}

