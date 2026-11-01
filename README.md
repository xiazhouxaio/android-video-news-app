# 短视频资讯 Android 客户端

一个基于 Java 的 Android 短视频与资讯客户端，配套一个无需 MySQL 的 Python 本地后端。
项目打开即可运行，支持在线视频流、实时资讯、点赞收藏和原生详情页。

## 功能特性

- **首页视频流**：在线抓取视频，下拉刷新随机换一批，点击即可播放
- **视频互动**：点赞、收藏、我的收藏
- **实时资讯**：今日头条热榜实时抓取，下拉刷新获取最新内容
- **原生资讯详情**：标题、作者、时间、评论数、新闻图片，一键查看原文
- **我的页面**：我的收藏、换肤
- **无需数据库**：本地后端使用 Python 标准库，不依赖 MySQL / Redis
- **无需登录**：打开 App 直接进入首页

## 技术栈

| 层级 | 技术 |
| --- | --- |
| Android | Java、AndroidX、OkHttp、Gson、Picasso、DKPlayer、SmartRefreshLayout、FlycoTabLayout |
| 本地后端 | Python 3 标准库、HTTP Server、Range 流式代理 |
| 构建 | Gradle 8.14.3、Android Gradle Plugin 8.13.2、JDK 21、compileSdk 36、minSdk 21 |
| 数据源 | Coverr 在线视频、今日头条热榜 |

## 项目结构

```text
android-video-news-app/
├── app/                       Android 客户端
│   └── src/main/
│       ├── java/com/ttit/myapp/
│       │   ├── activity/      首页、资讯详情、我的收藏
│       │   ├── adapter/       视频、资讯、收藏列表适配器
│       │   ├── api/           网络请求封装
│       │   ├── entity/        JSON 数据实体
│       │   ├── fragment/      首页、资讯、我的
│       │   └── view/          自定义控件
│       └── res/               布局、图片、主题
├── local-backend/             Python 本地后端
│   ├── server.py              视频/资讯抓取、媒体代理
│   └── static/                头像与兜底封面
├── start_backend.bat          启动后端并建立 adb reverse
└── README.md
```

## 运行环境

- Windows 10/11
- Android Studio（自带 Android SDK）
- JDK 21
- Android SDK Platform 36
- Python 3.10+
- 一台开启 USB 调试的 Android 手机

## 运行步骤

1. 用 Android Studio 打开项目根目录，等待 Gradle Sync 完成。
2. 双击项目根目录的 **`start_backend.bat`**，窗口保持打开。
   - 脚本会执行 `adb reverse tcp:8080 tcp:8080`，并启动 `local-backend/server.py`。
3. 手机通过 USB 连接电脑，允许 USB 调试。
4. 在 Android Studio 中点击 **Run 'app'**。
5. App 启动后直接进入首页，可下拉刷新视频和资讯。

> 手机需要保持 USB 连接；重新插拔手机后，重新双击 `start_backend.bat`。

## 本地后端

- 视频：从 Coverr 在线抓取，每次刷新重新随机排序。
- 资讯：从今日头条热榜在线抓取，每次刷新获取最新内容。
- 视频、封面、新闻图片通过本地 `/renren-fast/proxy` 转发，手机只访问 `127.0.0.1:8080`。
- 点赞和收藏保存在内存中，重启后端后重置。
- 无需安装 MySQL、Redis 或其他数据库。

## 项目地址

**https://gitee.com/xia-xiaolong666/android-video-news-app**

## 说明

- 在线数据源为公开接口，若接口调整或网络不可用，列表会使用本地兜底数据。
- 本项目仅用于学习与技术演示。
