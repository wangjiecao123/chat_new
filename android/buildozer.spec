[app]

# 应用名称
title = 极简聊天

# 包名
package.name = chat
package.domain = com.simplechat

# 源码目录
source.dir = .
source.include_exts = py,png,jpg,kv,atlas

# 版本
version = 1.0

# 需求（重要：需要包含common目录）
requirements = python3,kivy

# Android权限（必须有网络权限）
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE

# Android API级别
android.api = 30
android.minapi = 21
android.ndk = 23b

# 默认图标（可以自己准备图片）
# android.icon = icon.png
# android.rounded_icon = icon_rounded.png

# 存储权限（可选）
# android.permissions = INTERNET

# 全屏
# android.fullscreen = 0

# 日志
# android.logcat_filters = *:S python:D

[buildozer]

# 日志级别
log_level = 2

# 警告
warn_on_root = 1