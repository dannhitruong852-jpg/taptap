# 阮小咪 Android App

现有考研英语 C 模式网页的轻量 Android 外壳，不重新设计网页 UI。

- App 名称：阮小咪
- 打开后直接进入现有 Reader
- 不新增底部导航、设置页、独立播放器或额外启动页
- 6 张桌面图标按安装首日开始，每天顺延一张，6 天循环
- 图标切换双保险：WorkManager 每日后台检查 + 每次启动时立即校正
- Android 12+ 系统级极短启动画面仍由系统提供

Reader URL:
https://dannhitruong852-jpg.github.io/taptap/kaoyan-reader-v1/

构建:
gradle :app:assembleDebug
