"""Download NTU COOL (cool-video.dlc.ntu.edu.tw) lecture videos.

Usage:
    python ntu_cool_dl.py <url> [<url> ...] [-o OUTDIR] [--list]

<url> can be:
    https://cool.ntu.edu.tw/courses/67065                      -> every video in the course's modules
    https://cool.ntu.edu.tw/courses/67065/modules              -> same
    https://cool.ntu.edu.tw/courses/67065/modules/items/2682560 -> just that video

Auth: an NTU COOL access token (Account > Settings > "+ New Access Token").
Provide it with --token, the NTU_COOL_TOKEN env var, or a token.txt file next to this script.
"""

import argparse
import html.parser
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import requests

CANVAS = "https://cool.ntu.edu.tw"
VIDEO_HOST = "cool-video.dlc.ntu.edu.tw"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"


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


def load_token(cli_token):
    if cli_token:
        return cli_token.strip()
    if os.environ.get("NTU_COOL_TOKEN"):
        return os.environ["NTU_COOL_TOKEN"].strip()
    f = Path(__file__).with_name("token.txt")
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    sys.exit("No token. Create one at NTU COOL > Account > Settings > '+ New Access Token', "
             "then pass --token, set NTU_COOL_TOKEN, or save it to token.txt.")


def safe_name(s):
    s = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", s).strip(" .")
    return s[:150] or "video"


class Canvas:
    def __init__(self, token):
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}", "User-Agent": UA})

    def get(self, path, **params):
        r = self.s.get(path if path.startswith("http") else CANVAS + path, params=params)
        if r.status_code == 401:
            sys.exit("NTU COOL rejected the token (401). Check that it is correct and not expired.")
        r.raise_for_status()
        return r

    def paged(self, path, **params):
        r = self.get(path, per_page=100, **params)
        out = r.json()
        while "next" in r.links:
            r = self.get(r.links["next"]["url"])
            out += r.json()
        return out

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
        page = requests.get(url, headers={"User-Agent": UA}).text
        p = FormParser()
        p.feed(page)
        if not p.action:
            raise RuntimeError("launch page had no LTI form")
        return p.action, p.fields


def video_info(canvas, course_id, item_id):
    action, fields = canvas.launch_form(course_id, item_id)
    vs = requests.Session()
    vs.headers["User-Agent"] = UA
    r = vs.post(action, data=fields, headers={"Origin": CANVAS, "Referer": CANVAS + "/"})
    r.raise_for_status()
    m = re.search(r"/courses/(\d+)/videos/(\d+)", r.url)
    if not m:
        raise RuntimeError(f"unexpected landing page after LTI launch: {r.url}")
    api = f"https://{VIDEO_HOST}/api/courses/{m[1]}/videos/{m[2]}/view"
    info = vs.get(api)
    info.raise_for_status()
    return info.json()


def download_http(url, dest):
    part = dest.with_suffix(dest.suffix + ".part")
    have = part.stat().st_size if part.exists() else 0
    headers = {"User-Agent": UA}
    if have:
        headers["Range"] = f"bytes={have}-"
    with requests.get(url, headers=headers, stream=True, timeout=60) as r:
        if r.status_code == 416:  # already complete
            part.rename(dest)
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
    part.rename(dest)


def download_dash(mpd_url, dest):
    if shutil.which("yt-dlp"):
        cmd = ["yt-dlp", "-o", str(dest), "--merge-output-format", "mp4", mpd_url]
    elif shutil.which("ffmpeg"):
        cmd = ["ffmpeg", "-y", "-i", mpd_url, "-c", "copy", str(dest)]
    else:
        raise RuntimeError("no direct MP4 available and neither yt-dlp nor ffmpeg is installed")
    subprocess.run(cmd, check=True)


def parse_url(u):
    m = re.search(r"/courses/(\d+)(?:/modules/items/(\d+))?", u)
    if not m:
        sys.exit(f"Not an NTU COOL course / module item URL: {u}")
    return m[1], m[2]


def main():
    ap = argparse.ArgumentParser(description="Download NTU COOL videos.")
    ap.add_argument("urls", nargs="+", help="course URL or module item URL")
    ap.add_argument("-o", "--outdir", default="downloads", help="output folder (default: downloads)")
    ap.add_argument("--token", help="NTU COOL access token")
    ap.add_argument("--list", action="store_true", help="only list videos, don't download")
    args = ap.parse_args()

    canvas = Canvas(load_token(args.token))
    failures = 0
    for u in args.urls:
        course_id, item_id = parse_url(u)
        course = canvas.get(f"/api/v1/courses/{course_id}").json()
        items = canvas.video_items(course_id, item_id)
        print(f"[{course.get('name', course_id)}] {len(items)} video(s)")
        outdir = Path(args.outdir) / safe_name(course.get("course_code") or course.get("name") or course_id)

        for i, (mod, it) in enumerate(items, 1):
            label = f"{mod} - {it['title']}" if it["title"] not in mod else it["title"]
            print(f"({i}/{len(items)}) {label}")
            if args.list:
                continue
            try:
                info = video_info(canvas, course_id, it["id"])
                dest = outdir / f"{i:02d} {safe_name(label)}.mp4"
                if dest.exists():
                    print(f"  already have {dest}")
                    continue
                outdir.mkdir(parents=True, exist_ok=True)
                print(f"  -> {dest}  ({info.get('title')}, {info.get('length', 0) // 60} min)")
                if info.get("altSourceUri"):
                    download_http(info["altSourceUri"], dest)
                elif info.get("sourceUri"):
                    download_dash(info["sourceUri"], dest)
                else:
                    raise RuntimeError("video has no source URL")
            except Exception as e:
                failures += 1
                print(f"  FAILED: {e}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
