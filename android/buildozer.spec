[app]

# App info
title = Mitsu
package.name = mitsu
package.domain = com.virat013s.mitsu
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,json
version = 2.0.0
version.code = 2

# Requirements
requirements = python3,kivy,android,plyer,pyjnius,urllib3,certifi

# Permissions - comprehensive list for all features
android.permissions = INTERNET,RECORD_AUDIO,CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,VIBRATE,RECEIVE_BOOT_COMPLETED,SYSTEM_ALERT_WINDOW,WAKE_LOCK,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,READ_CONTACTS,READ_CALL_LOG,SEND_SMS,CALL_PHONE,ACCESS_WIFI_STATE,ACCESS_NETWORK_STATE,FLASHLIGHT,READ_CALENDAR,WRITE_CALENDAR,SET_ALARM,RECEIVE_SMS

# Android API - supports Android 5.0+ (API 21+)
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33

# Build for arm64 (most modern phones including Vivo/OriginOS)
android.archs = arm64-v8a
android.enable_split = False

# Gradle dependencies (not needed - we use plyer for all Android features)
# android.gradle_dependencies = com.google.android.gms:play-services-speech:21.0.0,com.google.android.gms:play-services-location:21.1.0,com.google.android.gms:play-services-vision:20.1.3

# P4A (python-for-android) recipe
p4a.branch = develop

# Presplash image
presplash.filename = %(source.dir)s/assets/img/presplash.png

# Icon
icon.filename = %(source.dir)s/assets/img/icon.png

# Orientation - portrait only
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

# Default assistant intent filters
android.add_android_manifest_intent = android.intent.action.ASSIST,android.intent.action.VOICE_COMMAND,android.intent.action.LONG_PRESS_POWER_KEY

# Service for background TTS and proactive messaging
android.services = mitsu_service:MitsuService

# Proguard (for release builds)
android.enable_proguard = False

# Android X
android.enable_androidx = True

# Play Store ready
android.enable_playstore = False
android.backups_allowed = True

# Build APK
[buildozer]
warn_on_root = 0
