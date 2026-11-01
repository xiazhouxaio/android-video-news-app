# 本地后端

一个仅使用 Python 标准库的本地 HTTP 服务，为 Android 客户端提供在线视频、实时资讯和媒体代理能力。
无需 MySQL、Redis 或其他数据库。

## 功能

- 在线视频列表：从 Coverr 抓取，按请求随机排序
- 实时资讯列表：从今日头条热榜抓取
- 媒体代理：转发在线视频、封面和新闻图片，支持 HTTP Range
- 点赞/收藏状态：内存保存
- 本地静态资源：头像和兜底封面

## 启动

在项目根目录双击 **`start_backend.bat`**。

脚本会：

1. 执行 `adb reverse tcp:8080 tcp:8080`，让手机通过 USB 访问电脑；
2. 启动 `server.py`。

看到 `Starting local backend` 即启动成功。首次启动会在后台抓取在线数据，请稍等几秒。

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/renren-fast/app/videocategory/list` | 视频分类 |
| GET | `/renren-fast/app/videolist/getListByCategoryId` | 视频列表（page=1 重新随机） |
| GET | `/renren-fast/app/videolist/listAll` | 全部视频 |
| GET | `/renren-fast/app/news/api/list` | 实时资讯列表 |
| GET | `/renren-fast/app/videolist/mycollect` | 我的收藏 |
| POST | `/renren-fast/app/videolist/updateCount` | 点赞/收藏 |
| GET | `/renren-fast/proxy` | 在线媒体代理（支持 Range） |
| GET | `/renren-fast/newsDetail` | 资讯详情页 |
| GET | `/renren-fast/static/*` | 本地静态图片 |

## 数据来源

- 视频：Coverr（https://coverr.co）
- 资讯：今日头条热榜（https://www.toutiao.com/hot-event/hot-board/）

## 说明

- 在线接口为公开接口，若不可用会使用兜底数据。
- 点赞/收藏保存在内存，重启服务后重置。
- 手机需保持 USB 连接，并由 `start_backend.bat` 建立 adb reverse。

## 项目地址

**https://gitee.com/xia-xiaolong666/android-video-news-app**
