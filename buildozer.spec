[app]
title = Мои Дела
package.name = mytodo
package.domain = org.mytodo
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt
source.exclude_dirs = .github, bin, .buildozer, __pycache__
version = 1.0
requirements = python3,kivy,requests,urllib3,chardet,idna,certifi,filetype
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 0
