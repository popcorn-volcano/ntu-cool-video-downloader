"""NTU COOL video downloader.

Downloads lecture videos hosted on NTU COOL's video platform (cool-video.dlc.ntu.edu.tw).

Run with no arguments (or double-click the .exe) for interactive mode, or:
    ntu_cool_dl <url> [<url> ...] [-o OUTDIR] [--list] [--all]

<url> can be a course link (https://cool.ntu.edu.tw/courses/67065)
or a single video link (https://cool.ntu.edu.tw/courses/67065/modules/items/2682560).
"""

import argparse
import html.parser
import os
import re
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

import requests

__version__ = "1.1.0"

CANVAS = "https://cool.ntu.edu.tw"
VIDEO_HOST = "cool-video.dlc.ntu.edu.tw"
TOKEN_PAGE = CANVAS + "/profile/settings"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"


class UserError(Exception):
    """An error with a message meant for the user (no traceback)."""


# ---------- token storage ----------

def config_dir():
    base = os.environ.get("APPDATA") if os.name == "nt" else os.environ.get("XDG_CONFIG_HOME")
    return Path(base or Path.home() / ".config") / "ntu-cool-dl"


def token_file():
    return config_dir() / "token.txt"


def saved_token():
    if os.environ.get("NTU_COOL_TOKEN"):
        return os.environ["NTU_COOL_TOKEN"].strip()
    f = token_file()
    return f.read_text(encoding="utf-8").strip() if f.exists() else None


def save_token(token):
    config_dir().mkdir(parents=True, exist_ok=True)
    token_file().write_text(token, encoding="utf-8")


def ask_token():
    print()
    print("第一次使用需要 NTU COOL 存取權杖 (Access Token)。First run: an NTU COOL access token is needed.")
    print("  1. 在開啟的網頁登入 NTU COOL（設定頁面）")
    print("  2. 往下找到「已核准的整合 Approved Integrations」，按「+ 新增存取權杖 / + New Access Token」")
    print("  3. 用途隨便填（例如 video），按「產生權杖」，複製那串很長的權杖")
    print(f"  (網址 URL: {TOKEN_PAGE})")
    try:
        webbrowser.open(TOKEN_PAGE)
    except Exception:
        pass
    token = input("\n貼上權杖後按 Enter / Paste token and press Enter: ").strip()
    if not token:
        raise UserError("沒有輸入權杖。No token entered.")
    return token


# ---------- NTU COOL (Canvas) API ----------

class Canvas:
    def __init__(self, token):
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}", "User-Agent": UA})

    def get(self, path, **params):
        try:
            r = self.s.get(path if path.startswith("http") else CANVAS + path, params=params, timeout=30)
        except requests.ConnectionError:
            raise UserError("連不到 NTU COOL，請檢查網路。Cannot reach NTU COOL; check your connection.")
        if r.status_code == 401:
            raise UserError("權杖無效或已過期。The token is invalid or expired.")
        if r.status_code in (403, 404):
            raise UserError(f"沒有權限或找不到：{path}（你有修這門課嗎？）"
                            f" Not found / no access (are you enrolled in this course?)")
        r.raise_for_status()
        return r

    def paged(self, path, **params):
        r = self.get(path, per_page=100, **params)
        out = r.json()
        while "next" in r.links:
            r = self.get(r.links["next"]["url"])
            out += r.json()
        return out

    def me(self):
        return self.get("/api/v1/users/self").json()

    def video_items(self, course_id, item_id=None):
        """Return [(module_name, module_item)] for cool-video items."""
        modules = self.paged(f"/api/v1/courses/{course_id}/modules", **{"include[]": "items"})
        out = []
        for m in modules:
            items = m.get("items")
            if items is None:  # large modules aren't inlined
                items = self.paged(f"/api/v1/courses/{course_id}/modules/{m['id']}/items")
            for it in items:
                if VIDEO_HOST not in (it.get("external_url") or ""):
                    continue
                if item_id and str(it["id"]) != str(item_id):
                    continue
                out.append((m["name"], it))
        return out

    def launch_form(self, course_id, item_id):
        url = self.get(f"/api/v1/courses/{course_id}/external_tools/sessionless_launch",
                       launch_type="module_item", module_item_id=item_id).json()["url"]
        # The verifier in the URL authenticates this request; no cookies needed.
        page = requests.get(url, headers={"User-Agent": UA}, timeout=30).text
        p = FormParser()
        p.feed(page)
        if not p.action:
            raise RuntimeError("launch page had no LTI form")
        return p.action, p.fields


class FormParser(html.parser.HTMLParser):
    """Grab the first <form> (the LTI launch form) and its inputs."""

    def __init__(self):
        super().__init__()
        self.action = None
        self.fields = {}
        self._in_form = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form" and self.action is None:
            self.action = a.get("action")
            self._in_form = True
        elif tag == "input" and self._in_form and a.get("name"):
            self.fields[a["name"]] = a.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self._in_form = False


def video_info(canvas, course_id, item_id):
    """Log in to cool-video through an LTI launch and return the video's metadata."""
    action, fields = canvas.launch_form(course_id, item_id)
    vs = requests.Session()
    vs.headers["User-Agent"] = UA
    r = vs.post(action, data=fields, headers={"Origin": CANVAS, "Referer": CANVAS + "/"}, timeout=30)
    r.raise_for_status()
    m = re.search(r"/courses/(\d+)/videos/(\d+)", r.url)
    if not m:
        raise RuntimeError(f"unexpected page after logging in to the video site: {r.url}")
    info = vs.get(f"https://{VIDEO_HOST}/api/courses/{m[1]}/videos/{m[2]}/view", timeout=30)
    info.raise_for_status()
    return info.json()


# ---------- downloading ----------

def download_http(url, dest):
    part = dest.with_name(dest.name + ".part")
    have = part.stat().st_size if part.exists() else 0
    headers = {"User-Agent": UA}
    if have:
        headers["Range"] = f"bytes={have}-"
        print(f"  從 {have / 1e6:.0f} MB 繼續 / resuming")
    with requests.get(url, headers=headers, stream=True, timeout=60) as r:
        if r.status_code == 416:  # already complete
            part.replace(dest)
            return
        r.raise_for_status()
        if have and r.status_code != 206:
            have = 0  # server ignored Range; start over
        total = int(r.headers.get("Content-Length", 0)) + have
        done = have
        with open(part, "ab" if have else "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r  {done / 1e6:8.1f} / {total / 1e6:.1f} MB  ({done * 100 / total:5.1f}%)",
                          end="", flush=True)
    print()
    part.replace(dest)


def download_dash(mpd_url, dest):
    if shutil.which("yt-dlp"):
        cmd = ["yt-dlp", "-o", str(dest), "--merge-output-format", "mp4", mpd_url]
    elif shutil.which("ffmpeg"):
        cmd = ["ffmpeg", "-y", "-i", mpd_url, "-c", "copy", str(dest)]
    else:
        raise UserError("這部影片沒有 MP4 檔，需要安裝 ffmpeg 才能下載。"
                        "This video has no MP4; install ffmpeg to download it.")
    subprocess.run(cmd, check=True)


# ---------- helpers ----------

def safe_name(s):
    s = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", str(s)).strip(" .")
    return s[:150] or "video"


def parse_url(u):
    if VIDEO_HOST in u:
        raise UserError(f"請貼 cool.ntu.edu.tw 的網址，不是影片播放器的網址：{u}\n"
                        "  Use the cool.ntu.edu.tw link (from the course's Modules page), not the player link.")
    m = re.search(r"cool\.ntu\.edu\.tw/courses/(\d+)(?:/modules/items/(\d+))?", u)
    if not m:
        raise UserError(f"看不懂這個網址 / Not an NTU COOL course or video link: {u}")
    return m[1], m[2]


def parse_selection(text, n):
    """'all' / '' -> everything; '1,3,5-7' -> those numbers (1-based)."""
    text = text.strip().lower()
    if text in ("", "a", "all"):
        return list(range(1, n + 1))
    picked = set()
    for part in re.split(r"[,\s]+", text):
        if not part:
            continue
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", part)
        if not m:
            raise UserError(f"看不懂的選擇 / Bad selection: {part}")
        a, b = int(m[1]), int(m[2] or m[1])
        picked.update(i for i in range(a, b + 1) if 1 <= i <= n)
    return sorted(picked)


def default_outdir():
    downloads = Path.home() / "Downloads"
    return (downloads if downloads.exists() else Path.home()) / "NTU COOL Videos"


# ---------- main ----------

def run(args, interactive):
    token = args.token or saved_token()
    newly_entered = False
    if not token:
        if not interactive:
            raise UserError("No token. Run without arguments once to set it up, or pass --token.")
        token = ask_token()
        newly_entered = True
    canvas = Canvas(token)
    try:
        me = canvas.me()
    except UserError:
        if newly_entered or args.token:
            raise
        # Saved token stopped working: ask for a new one.
        print("已儲存的權杖失效了。The saved token no longer works.")
        if not interactive:
            raise
        token = ask_token()
        newly_entered = True
        canvas = Canvas(token)
        me = canvas.me()
    if newly_entered and not args.token:
        save_token(token)
        print(f"權杖已儲存於 / Token saved to {token_file()}")
    print(f"登入身分 / Logged in as: {me.get('name')}")

    urls = args.urls
    if not urls:
        print("\n貼上課程或影片網址（可以多個，用空白分隔）")
        print("Paste a course or video link (several allowed, separated by spaces)")
        print("  例 e.g. https://cool.ntu.edu.tw/courses/12345")
        urls = input("> ").split()
        if not urls:
            raise UserError("沒有輸入網址。No link entered.")

    outroot = Path(args.outdir) if args.outdir else default_outdir()
    failures = 0
    for u in urls:
        course_id, item_id = parse_url(u)
        course = canvas.get(f"/api/v1/courses/{course_id}").json()
        items = canvas.video_items(course_id, item_id)
        print(f"\n[{course.get('name', course_id)}] 找到 {len(items)} 部影片 / video(s)")
        if not items:
            print("  （只會找「單元 Modules」頁面裡的影片 / Only videos on the Modules page are found）")
            continue
        labels = [f"{mod} - {it['title']}" if it["title"] not in mod else it["title"] for mod, it in items]
        for i, label in enumerate(labels, 1):
            print(f"  {i:2d}. {label}")
        if args.list:
            continue

        chosen = list(range(1, len(items) + 1))
        if interactive and not item_id and len(items) > 1 and not args.all:
            sel = input("\n要下載哪些？Enter = 全部，或輸入編號如 1,3,5-7\n"
                        "Which ones? Enter = all, or numbers like 1,3,5-7\n> ")
            chosen = parse_selection(sel, len(items))

        outdir = outroot / safe_name(course.get("course_code") or course.get("name") or course_id)
        for i in chosen:
            mod, it = items[i - 1]
            dest = outdir / f"{i:02d} {safe_name(labels[i - 1])}.mp4"
            print(f"\n({i}/{len(items)}) {labels[i - 1]}")
            if dest.exists():
                print("  已下載過，略過 / already downloaded, skipping")
                continue
            try:
                info = video_info(canvas, course_id, it["id"])
                outdir.mkdir(parents=True, exist_ok=True)
                print(f"  -> {dest}")
                if info.get("altSourceUri"):
                    download_http(info["altSourceUri"], dest)
                elif info.get("sourceUri"):
                    download_dash(info["sourceUri"], dest)
                else:
                    raise UserError("找不到影片來源 / video has no source")
            except KeyboardInterrupt:
                raise
            except Exception as e:
                failures += 1
                print(f"  失敗 FAILED: {e}")

    if not args.list:
        print(f"\n完成！檔案在 / Done! Files are in: {outroot}")
        if failures:
            print(f"有 {failures} 部失敗，可以再執行一次重試。{failures} failed; run again to retry.")
    return 1 if failures else 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="ntu_cool_dl", description="Download NTU COOL lecture videos.")
    ap.add_argument("urls", nargs="*", help="course link or video link (omit for interactive mode)")
    ap.add_argument("-o", "--outdir", help="output folder (default: Downloads/NTU COOL Videos)")
    ap.add_argument("--token", help="NTU COOL access token (otherwise the saved one is used)")
    ap.add_argument("--list", action="store_true", help="only list videos, don't download")
    ap.add_argument("--all", action="store_true", help="download every video without asking")
    ap.add_argument("--forget-token", action="store_true", help="delete the saved token and exit")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args()

    if args.forget_token:
        token_file().unlink(missing_ok=True)
        print("已刪除儲存的權杖。Saved token deleted.")
        return

    interactive = not args.urls
    if interactive:
        print(f"NTU COOL 影片下載工具 / Video Downloader v{__version__}")
    code = 0
    try:
        code = run(args, interactive)
    except UserError as e:
        print(f"\n錯誤 Error: {e}")
        code = 1
    except KeyboardInterrupt:
        print("\n已中斷。下次執行會從中斷處繼續。Interrupted; the next run resumes.")
        code = 130
    if interactive:  # keep the window open when launched by double-click
        try:
            input("\n按 Enter 結束 / Press Enter to exit")
        except (EOFError, KeyboardInterrupt):
            pass
    sys.exit(code)


if __name__ == "__main__":
    main()
