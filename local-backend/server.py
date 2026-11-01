# -*- coding: utf-8 -*-
"""
myapp 本地后端（无需 MySQL，不内置视频）

视频列表实时从 Coverr（https://coverr.co）在线抓取，每次下拉刷新
（page=1）都会重新随机排序并返回一批新视频。视频和封面通过本地
/proxy 转发，手机只需要访问 127.0.0.1:8080。
"""

import html
import json
import mimetypes
import os
import random
import re
import threading
import time
import urllib.error
import urllib.request
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlsplit

HOST = "0.0.0.0"
PORT = 8080
BASE = "/renren-fast"
PUBLIC_BASE = "http://127.0.0.1:8080"   # 手机通过 adb reverse 访问电脑

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, "static")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# ---------------------------------------------------------------------------
# 固定数据
# ---------------------------------------------------------------------------
CATEGORIES = [
    {"categoryId": 1, "categoryName": "推荐"},
]

FALLBACK_NEWS = [
    {"newsId": 1, "newsTitle": "《忍者蛙》发售日公布 已上架Steam、支持简中", "authorName": "3DMGAME",
     "commentCount": 3, "releaseDate": "2020-07-31 22:23:00", "type": 1, "thumbs": [1]},
    {"newsId": 2, "newsTitle": "外媒爆料：育碧“阿瓦隆”项目胎死腹中，只因为他不喜欢奇幻游戏", "authorName": "爱游戏的萌博士",
     "commentCount": 1, "releaseDate": "2020-07-31 21:01:17", "type": 2, "thumbs": [2, 3, 4]},
    {"newsId": 3, "newsTitle": "索尼公布Ready for PlayStation 5电视阵容", "authorName": "游戏时光VGtime",
     "commentCount": 6, "releaseDate": "2020-07-30 13:11:32", "type": 3, "thumbs": [5]},
    {"newsId": 4, "newsTitle": "一部不受关注的互动电影佳作——解构《暴雨》", "authorName": "瑾瑜游乐说",
     "commentCount": 12, "releaseDate": "2020-07-30 13:11:32", "type": 3, "thumbs": [6]},
    {"newsId": 5, "newsTitle": "《光环：无限》官方Q&A 无充值战利品，画质优化中", "authorName": "聚玩社官方",
     "commentCount": 4, "releaseDate": "2020-08-01 08:22:47", "type": 2, "thumbs": [7, 8, 9]},
    {"newsId": 6, "newsTitle": "2020小编个人力推的耐玩的养老游戏", "authorName": "游戏我看看",
     "commentCount": 7, "releaseDate": "2020-07-30 12:48:37", "type": 1, "thumbs": [10]},
    {"newsId": 7, "newsTitle": "NBA复赛赛况：开拓者加时擒灰熊，太阳胜奇才，魔术“主场”破网", "authorName": "头条专题",
     "commentCount": 23, "releaseDate": "2020-08-01 06:49:44", "type": 1, "thumbs": [11]},
    {"newsId": 8, "newsTitle": "NBA最有含金量总冠军？奥拉朱旺95年4次以下克上！无冠军超过2次", "authorName": "网罗篮球",
     "commentCount": 45, "releaseDate": "2020-05-23 14:08:09", "type": 2, "thumbs": [12, 13, 14]},
]

NEWS_COVERS = [
    PUBLIC_BASE + "/static/c1.png",
    PUBLIC_BASE + "/static/c2.png",
    PUBLIC_BASE + "/static/c3.png",
    PUBLIC_BASE + "/static/c4.jpg",
    PUBLIC_BASE + "/static/c5.jpg",
    PUBLIC_BASE + "/static/c6.jpg",
]

AVATAR_URLS = [
    PUBLIC_BASE + "/static/a1.png",
    PUBLIC_BASE + "/static/a2.png",
    PUBLIC_BASE + "/static/a3.png",
]

LOCK = threading.Lock()
FETCH_LOCK = threading.Lock()

# 直接连外网，不走系统代理
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

# 在线视频源
COVERR_URL = "https://coverr.co/"
COVERR_TTL = 300  # 5 分钟内不重复下载页面，但每次刷新仍会重新随机排序
ALLOWED_PROXY_HOSTS = {
    "cdn.coverr.co",
    "media.w3.org",
    "vjs.zencdn.net",
    "test-videos.co.uk",
}

NEWS_URL = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
NEWS_TTL = 60  # 热榜缓存 60 秒


def proxy_allowed(host):
    if not host:
        return False
    return host in ALLOWED_PROXY_HOSTS or host.endswith(".toutiaoimg.com")

# 在线源不可用时的兜底（仍然是网络视频，不打包进 App）
FALLBACK_ENTRIES = [
    {"slug": "sintel-trailer", "title": "Sintel 预告片",
     "video_url": "https://media.w3.org/2010/05/sintel/trailer.mp4",
     "thumb_url": "https://media.w3.org/2010/05/sintel/poster.png"},
    {"slug": "big-buck-bunny-trailer", "title": "Big Buck Bunny 预告片",
     "video_url": "https://media.w3.org/2010/05/bunny/trailer.mp4",
     "thumb_url": "https://media.w3.org/2010/05/bunny/poster.png"},
    {"slug": "oceans", "title": "Oceans 海洋",
     "video_url": "https://vjs.zencdn.net/v/oceans.mp4",
     "thumb_url": "https://vjs.zencdn.net/v/oceans.png"},
    {"slug": "jellyfish", "title": "Jellyfish 水母",
     "video_url": "https://test-videos.co.uk/vids/jellyfish/mp4/h264/360/Jellyfish_360_10s_1MB.mp4",
     "thumb_url": "https://test-videos.co.uk/user/pages/images/jellyfish.jpg"},
    {"slug": "sintel-10s", "title": "Sintel 10 秒片段",
     "video_url": "https://test-videos.co.uk/vids/sintel/mp4/h264/360/Sintel_360_10s_1MB.mp4",
     "thumb_url": "https://test-videos.co.uk/user/pages/images/sintel.jpg"},
    {"slug": "bbb-10s", "title": "Big Buck Bunny 10 秒片段",
     "video_url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4",
     "thumb_url": "https://test-videos.co.uk/user/pages/images/big_buck_bunny.jpg"},
    {"slug": "w3c-movie", "title": "W3C 示例短片",
     "video_url": "https://media.w3.org/2010/05/video/movie_300.mp4",
     "thumb_url": "https://media.w3.org/2010/05/video/poster.png"},
]

_cache = {"entries": [], "fetched_at": 0.0}
_feed = {"order": []}
_video_state = {}
_entry_by_vid = {}
_news_cache = {"entries": [], "fetched_at": 0.0}


# ---------------------------------------------------------------------------
# Coverr 抓取与解析
# ---------------------------------------------------------------------------
def slug_to_title(slug):
    s = re.sub(r"^coverr-", "", slug)
    s = re.sub(r"-\d+$", "", s)
    s = s.replace("-", " ").strip()
    return " ".join(w[:1].upper() + w[1:] for w in s.split())


def fetch_coverr(force=False):
    now = time.time()
    with LOCK:
        if not force and _cache["entries"] and now - _cache["fetched_at"] < COVERR_TTL:
            return list(_cache["entries"])

    with FETCH_LOCK:
        with LOCK:
            if not force and _cache["entries"] and time.time() - _cache["fetched_at"] < COVERR_TTL:
                return list(_cache["entries"])

        try:
            req = urllib.request.Request(COVERR_URL, headers={"User-Agent": UA})
            with OPENER.open(req, timeout=30) as resp:
                page = resp.read().decode("utf-8", "ignore")

            videos = {}
            rank = {"360p": 0, "720p": 1, "1080p": 2, "original": 3}
            for m in re.finditer(
                    r'https://cdn\.coverr\.co/videos/([^/\s]+)/(360p|720p|1080p|original)\.mp4',
                    page):
                slug, res = m.group(1), m.group(2)
                if slug not in videos or rank[res] < rank[videos[slug]]:
                    videos[slug] = res

            titles = {}
            for m in re.finditer(
                    r'alt="([^"]*)"[^>]*?src="https://cdn\.coverr\.co/videos/([^/"]+)/thumbnail',
                    page):
                slug = m.group(2)
                title = html.unescape(m.group(1)).strip()
                if title:
                    titles[slug] = title

            entries = []
            for slug, res in videos.items():
                title = titles.get(slug) or slug_to_title(slug)
                low = title.lower()
                # 过滤临时素材和付费预览素材
                if ("temp-" in slug or low.startswith("temp ")
                        or low.startswith("premium ") or "mp4" in low):
                    continue
                if not title:
                    continue
                entries.append({
                    "slug": slug,
                    "title": title,
                    "video_url": "https://cdn.coverr.co/videos/%s/%s.mp4" % (slug, res),
                    "thumb_url": ("https://cdn.coverr.co/videos/%s/thumbnail"
                                  "?width=520&format=jpg" % slug),
                })

            if entries:
                with LOCK:
                    _cache["entries"] = entries
                    _cache["fetched_at"] = time.time()
                print("Coverr 在线视频: %d 条" % len(entries))
                return list(entries)
            print("Coverr 页面中未解析到视频，使用兜底列表")
        except Exception as e:
            print("Coverr 获取失败: %s" % e)

    with LOCK:
        if _cache["entries"]:
            return list(_cache["entries"])
    return list(FALLBACK_ENTRIES)


def stable_vid(slug):
    v = zlib.crc32(slug.encode("utf-8")) & 0x7FFFFFFF
    return v or 1


def ensure_state(vid):
    with LOCK:
        if vid not in _video_state:
            _video_state[vid] = {
                "commentnum": (vid * 7) % 300 + 5,
                "likenum": (vid * 13) % 900 + 20,
                "collectnum": (vid * 17) % 400 + 10,
                "flagLike": False,
                "flagCollect": False,
            }
        return dict(_video_state[vid])


def proxy_url(remote, ext="mp4"):
    # 路径带 .mp4/.jpg 后缀，部分播放器/图片库会据此判断类型
    return PUBLIC_BASE + BASE + "/proxy." + ext + "?url=" + quote(remote, safe="")


def video_json(entry):
    vid = stable_vid(entry["slug"])
    with LOCK:
        _entry_by_vid[vid] = entry
    state = ensure_state(vid)
    return {
        "vid": vid,
        "vtitle": entry["title"],
        "author": "Coverr",
        "coverurl": proxy_url(entry["thumb_url"], "jpg"),
        "headurl": AVATAR_URLS[vid % len(AVATAR_URLS)],
        "playurl": proxy_url(entry["video_url"], "mp4"),
        "createTime": "2026-10-26 00:00:00",
        "updateTime": time.strftime("%Y-%m-%d %H:%M:%S"),
        "categoryId": 1,
        "categoryName": "推荐",
        "videoSocialEntity": state,
    }


def feed_page(page, limit):
    page = max(1, int(page or 1))
    limit = max(1, int(limit or 5))

    if page == 1:
        entries = list(fetch_coverr(force=False))
        random.shuffle(entries)
        with LOCK:
            _feed["order"] = entries
    else:
        with LOCK:
            entries = list(_feed["order"])
        if not entries:
            entries = list(fetch_coverr(force=False))
            random.shuffle(entries)
            with LOCK:
                _feed["order"] = entries

    total = len(entries)
    start = (page - 1) * limit
    return entries[start:start + limit], total, page, limit


def legacy_entries():
    """今日头条热榜不可用时的兜底资讯。"""
    out = []
    for n in FALLBACK_NEWS:
        thumbs = [NEWS_COVERS[(n["newsId"] + i) % len(NEWS_COVERS)]
                  for i in range(len(n["thumbs"]))]
        out.append({
            "newsId": n["newsId"],
            "newsTitle": n["newsTitle"],
            "authorName": n["authorName"],
            "headerUrl": NEWS_COVERS[(n["newsId"] - 1) % len(NEWS_COVERS)],
            "commentCount": n["commentCount"],
            "releaseDate": n["releaseDate"],
            "type": n["type"],
            "url": "",
            "thumbs": thumbs,
        })
    return out


def fetch_news(force=False):
    """从今日头条热榜抓取实时资讯，失败时用缓存或兜底数据。"""
    now = time.time()
    with LOCK:
        if not force and _news_cache["entries"] and now - _news_cache["fetched_at"] < NEWS_TTL:
            return list(_news_cache["entries"])

    try:
        req = urllib.request.Request(NEWS_URL, headers={"User-Agent": UA})
        with OPENER.open(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", "ignore"))

        entries = []
        for i, item in enumerate(data.get("data") or []):
            title = (item.get("Title") or "").strip()
            if not title:
                continue
            img = ((item.get("Image") or {}).get("url") or "").strip()
            try:
                hot = int(item.get("HotValue") or 0)
            except (TypeError, ValueError):
                hot = 0
            entries.append({
                "newsId": i + 1,
                "newsTitle": html.unescape(title),
                "authorName": "今日头条热榜",
                "headerUrl": AVATAR_URLS[i % len(AVATAR_URLS)],
                "commentCount": max(1, min(9999, hot // 10000 + 3)),
                "releaseDate": time.strftime("%Y-%m-%d %H:%M:%S"),
                "type": 1,
                "url": item.get("Url") or "",
                "thumbs": [proxy_url(img, "jpg") if img
                           else NEWS_COVERS[i % len(NEWS_COVERS)]],
            })

        if entries:
            with LOCK:
                _news_cache["entries"] = entries
                _news_cache["fetched_at"] = time.time()
            print("今日头条热榜: %d 条" % len(entries))
            return entries
        print("今日头条热榜: 没有解析到数据")
    except Exception as e:
        print("今日头条热榜获取失败: %s" % e)

    with LOCK:
        if _news_cache["entries"]:
            return list(_news_cache["entries"])
    return legacy_entries()


def news_json(n):
    thumbs = n.get("thumbs") or [NEWS_COVERS[0]]
    return {
        "newsId": n["newsId"],
        "newsTitle": n["newsTitle"],
        "authorName": n["authorName"],
        "headerUrl": n.get("headerUrl") or NEWS_COVERS[0],
        "commentCount": n["commentCount"],
        "releaseDate": n["releaseDate"],
        "type": n["type"],
        "url": n.get("url", ""),
        "thumbEntities": [
            {"thumbId": n["newsId"] * 10 + i,
             "thumbUrl": url,
             "newsId": n["newsId"]}
            for i, url in enumerate(thumbs)
        ],
    }


def page_payload(items, page, limit, mapper):
    page = max(1, int(page or 1))
    limit = max(1, int(limit or 10))
    total = len(items)
    start = (page - 1) * limit
    return {
        "totalCount": total,
        "pageSize": limit,
        "totalPage": (total + limit - 1) // limit,
        "currPage": page,
        "list": [mapper(x) for x in items[start:start + limit]],
    }


NEWS_DETAIL_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
  body{margin:0;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#f5f5f5;color:#222}
  header{background:#e21918;color:#fff;padding:14px 16px;font-size:17px;font-weight:600}
  .wrap{padding:18px;background:#fff;margin:12px;border-radius:10px;line-height:1.8;font-size:15px}
  .hint{color:#888;font-size:13px;margin-top:16px}
  button{margin:0 12px 18px;padding:12px 18px;width:calc(100% - 24px);border:0;border-radius:8px;background:#e21918;color:#fff;font-size:16px}
</style>
</head>
<body>
<header>资讯详情</header>
<div class="wrap">
  <h3>__TITLE__</h3>
  <p>这是本地后端返回的资讯详情页。</p>
  <p>资讯、视频、点赞、收藏等接口均由本地服务提供。</p>
  <p class="hint">如果你看到这个页面，说明手机和电脑的本地服务已经连通。</p>
</div>
<button onclick="try{window.WebViewJavascriptBridge.callHandler('goback');}catch(e){history.back();}">返回</button>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "myapp-local/2.0"

    # ------------------------------------------------------------------ utils
    def log_message(self, fmt, *args):
        # 视频代理和静态资源请求很多，不打印，避免刷屏
        if "/proxy" in self.path or "/static/" in self.path:
            return
        print("[%s] %s" % (time.strftime("%H:%M:%S"), fmt % args))

    def _send_bytes(self, data, ctype, status=200, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send_bytes(data, "application/json; charset=utf-8", status)

    def _html(self, html_text, status=200):
        self._send_bytes(html_text.encode("utf-8"), "text/html; charset=utf-8", status)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            text = raw.decode("utf-8", "ignore")
            return {k: v[0] for k, v in parse_qs(text).items()}

    def _serve_static(self, name):
        # 只允许访问 static 目录下的文件名，防止目录穿越
        name = os.path.basename(name)
        path = os.path.join(STATIC_DIR, name)
        if not name or not os.path.isfile(path):
            self._json({"msg": "not found", "code": 404}, 404)
            return
        size = os.path.getsize(path)
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng.strip())
            if m:
                start = int(m.group(1)) if m.group(1) else 0
                end = int(m.group(2)) if m.group(2) else size - 1
                if start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", "bytes */%d" % size)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                end = min(end, size - 1)
                length = end - start + 1
                self.send_response(206)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(length))
                self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                if self.command != "HEAD":
                    with open(path, "rb") as f:
                        f.seek(start)
                        remain = length
                        while remain > 0:
                            chunk = f.read(min(65536, remain))
                            if not chunk:
                                break
                            try:
                                self.wfile.write(chunk)
                            except (BrokenPipeError, ConnectionResetError):
                                break
                            remain -= len(chunk)
                return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError):
                        break

    def _proxy(self):
        q = {k: v[0] for k, v in parse_qs(urlsplit(self.path).query).items()}
        target = q.get("url", "")
        u = urlsplit(target)
        if u.scheme not in ("http", "https") or not proxy_allowed(u.hostname):
            self._json({"msg": "forbidden", "code": 403}, 403)
            return

        headers = {"User-Agent": UA}
        rng = self.headers.get("Range")
        if rng:
            headers["Range"] = rng
        method = "HEAD" if self.command == "HEAD" else "GET"

        try:
            req = urllib.request.Request(target, headers=headers, method=method)
            resp = OPENER.open(req, timeout=30)
        except urllib.error.HTTPError as e:
            try:
                body = e.read()
            except Exception:
                body = b""
            ctype = e.headers.get("Content-Type", "application/octet-stream") if e.headers else "application/octet-stream"
            self._send_bytes(body, ctype, e.code)
            return
        except Exception as e:
            self._json({"msg": "proxy error: %s" % e, "code": 502}, 502)
            return

        try:
            status = resp.getcode()
            self.send_response(status)
            for h in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"):
                val = resp.headers.get(h)
                if val is not None:
                    self.send_header(h, val)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            if resp.headers.get("Content-Length") is None:
                self.send_header("Connection", "close")
                self.close_connection = True
            self.end_headers()
            if self.command != "HEAD":
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            try:
                resp.close()
            except Exception:
                pass

    # ----------------------------------------------------------------- routing
    def do_OPTIONS(self):
        self._send_bytes(b"", "text/plain", 204)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parts = urlsplit(self.path)
        path = parts.path
        q = {k: v[0] for k, v in parse_qs(parts.query).items()}

        if path.startswith(BASE):
            path = path[len(BASE):] or "/"

        if path.startswith("/proxy"):
            self._proxy()
            return

        if path == "/" or path == "":
            self._json({"msg": "myapp local backend", "code": 0,
                        "video_source": COVERR_URL,
                        "note": "每次 page=1 刷新会重新随机排序"})
            return

        if path.startswith("/static/"):
            self._serve_static(path[len("/static/"):])
            return

        if path == "/newsDetail":
            title = html.escape(q.get("title", "资讯详情"))
            self._html(NEWS_DETAIL_HTML.replace("__TITLE__", title))
            return

        if path == "/app/news/api/list":
            try:
                page_no = int(q.get("page") or 1)
            except ValueError:
                page_no = 1
            # 下拉刷新（page=1）强制拉最新热榜；翻页用缓存，保证顺序一致
            news_items = fetch_news(force=(page_no <= 1))
            payload = page_payload(news_items, page_no, q.get("limit"), news_json)
            self._json({"msg": "success", "code": 0, "page": payload})
            return

        if path == "/app/videocategory/list":
            payload = {
                "totalCount": len(CATEGORIES),
                "pageSize": 10,
                "totalPage": 1,
                "currPage": 1,
                "list": CATEGORIES,
            }
            self._json({"msg": "success", "code": 0, "page": payload})
            return

        if path in ("/app/videolist/listAll", "/app/videolist/getListByCategoryId"):
            items, total, page, limit = feed_page(q.get("page"), q.get("limit"))
            payload = {
                "totalCount": total,
                "pageSize": limit,
                "totalPage": (total + limit - 1) // limit if total else 0,
                "currPage": page,
                "list": [video_json(e) for e in items],
            }
            self._json({"msg": "success", "code": 0, "page": payload})
            return

        if path == "/app/videolist/mycollect":
            with LOCK:
                entries = [e for vid, e in _entry_by_vid.items()
                           if _video_state.get(vid, {}).get("flagCollect")]
            self._json({"msg": "success", "code": 0,
                        "list": [video_json(e) for e in entries]})
            return

        self._json({"msg": "not found: " + path, "code": 404}, 404)

    def do_POST(self):
        parts = urlsplit(self.path)
        path = parts.path
        if path.startswith(BASE):
            path = path[len(BASE):] or "/"
        body = self._body()

        if path == "/app/videolist/updateCount":
            try:
                vid = int(body.get("vid", 0))
                typ = int(body.get("type", -1))
                flag = bool(body.get("flag", False))
            except (TypeError, ValueError):
                self._json({"msg": "参数错误", "code": 500})
                return
            ensure_state(vid)
            with LOCK:
                st = _video_state[vid]
                if typ == 1 and flag != st["flagCollect"]:
                    st["collectnum"] = max(0, st["collectnum"] + (1 if flag else -1))
                    st["flagCollect"] = flag
                elif typ == 2 and flag != st["flagLike"]:
                    st["likenum"] = max(0, st["likenum"] + (1 if flag else -1))
                    st["flagLike"] = flag
            self._json({"msg": "success", "code": 0})
            return

        self._json({"msg": "not found: " + path, "code": 404}, 404)


def main():
    print("=" * 64)
    print("myapp 本地后端已启动（无需 MySQL，不内置视频）")
    print("监听: http://0.0.0.0:%d%s" % (PORT, BASE))
    print("视频源: %s（在线抓取）" % COVERR_URL)
    print("每次下拉刷新（page=1）会重新随机排序，返回新一批视频")
    print("手机端请先执行: adb reverse tcp:8080 tcp:8080")
    print("首次启动会在后台抓取视频列表，请稍等几秒")
    print("按 Ctrl+C 停止")
    print("=" * 64)

    # 后台预热在线视频和今日头条热榜，避免第一次刷新等太久
    threading.Thread(target=fetch_coverr, kwargs={"force": True}, daemon=True).start()
    threading.Thread(target=fetch_news, kwargs={"force": True}, daemon=True).start()

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
