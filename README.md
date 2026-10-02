# NTU COOL Video Downloader

Downloads lecture videos hosted on NTU COOL's video platform (`cool-video.dlc.ntu.edu.tw`).

## Setup (once)

1. In NTU COOL go to **Account → Settings → Approved Integrations → + New Access Token**, and copy the token.
2. Save it in a file named `token.txt` next to `ntu_cool_dl.py`. You can also set the `NTU_COOL_TOKEN` environment variable or pass `--token`.
   Keep this token private. Anyone who has it can act as you on NTU COOL. Delete it from the settings page when you're done.

Requires Python with `requests`. `yt-dlp` or `ffmpeg` is used only as a fallback when no direct MP4 is available.

## Usage

```
python ntu_cool_dl.py https://cool.ntu.edu.tw/courses/67065/modules/items/2682560   # one video
python ntu_cool_dl.py https://cool.ntu.edu.tw/courses/67065                         # every video in the course
python ntu_cool_dl.py https://cool.ntu.edu.tw/courses/67065 --list                  # just list them
python ntu_cool_dl.py <url> -o D:\Lectures                                         # choose output folder
```

Files go to `downloads/<course code>/NN <module> - <title>.mp4`. Videos you already have are skipped, and interrupted downloads resume.

## How it works

1. The Canvas API lists module items that point at cool-video.
2. For each one, the Canvas `sessionless_launch` API returns a signed LTI launch form. Submitting it logs in to cool-video.
3. cool-video's `/api/courses/<c>/videos/<v>/view` returns a presigned `transcoded.mp4` link (valid about 3 hours), which is downloaded directly.
