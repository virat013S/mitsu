[app]

# App info
title = Mitsu
package.name = mitsu
package.domain = com.virat013s.mitsu
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,json
version = 1.0.0
version.code = 1

# Requirements
requirements = python3,kivy,android,plyer,pyjnius,urllib3,certifi
# PIL for image processing (optional, can remove if not needed)
# requirements += pillow

# Permissions
android.permissions = INTERNET,RECORD_AUDIO,CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,VIBRATE,RECEIVE_BOOT_COMPLETED,SYSTEM_ALERT_WINDOW,WAKE_LOCK

# Android API
android.api = 33
android.minapi = 24
android.ndk = 25b
android.sdk = 33

# Build settings
android.arch = arm64-v8a
# Options: armeabi-v7a, arm64-v8a, x86, x86_64

# Gradle dependencies (for Android-specific features)
android.gradle_dependencies = com.google.android.gms:play-services-speech:19.0.1

# P4A (python-for-android) recipe
p4a.branch = develop

# Icon and presplash
# icon.filename = %(source.dir)s/assets/img/icon.png
# presplash.filename = %(source.dir)s/assets/img/presplash.png

# Orientation
orientation = portrait

# Fullscreen
fullscreen = 1

# Console (set to 0 for release builds)
log_level = 2

# Android specific
android.release_artifact = apk
android.skip_update = False

# Allow backup
android.allow_backup = True

# Private storage
android.private_storage = True

# SMS permission (not needed, remove if causes issues)
# android.add_android_manifest_activity = org.kivy.android.PythonActivity

# Service (for background TTS, optional)
# android.services = mitsu_service:MitsuService

# Proguard (for release builds)
android.enable_proguard = False

# Split APK by ABI (for smaller downloads)
android.enable_split = False

# Android X
android.enable_androidx = True

# Build APK
[buildozer]
warn_on_root = 0
