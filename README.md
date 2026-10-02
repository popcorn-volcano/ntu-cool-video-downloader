# NTU COOL 影片下載工具

把 NTU COOL 課程裡的上課影片（cool-video 播放器）下載成 MP4，方便離線複習。
可以一次下載整門課的所有影片，中斷後再執行會自動接續。

> English instructions are [below](#english).

---

## 下載

| 系統 | 下載 |
|---|---|
| Windows | [NTU-COOL-Downloader-Windows.exe](https://github.com/popcorn-volcano/ntu-cool-video-downloader/releases/latest/download/NTU-COOL-Downloader-Windows.exe) |
| macOS | [NTU-COOL-Downloader-macOS.zip](https://github.com/popcorn-volcano/ntu-cool-video-downloader/releases/latest/download/NTU-COOL-Downloader-macOS.zip) |

不需要安裝 Python 或其他東西，下載後直接打開即可。

## 使用步驟

### 1. 打開程式

- **Windows**：雙擊 `NTU-COOL-Downloader-Windows.exe`。
  如果跳出「Windows 已保護您的電腦」，按 **其他資訊 → 仍要執行**。（這是因為程式沒有付費簽章，不是病毒。）
- **macOS**：解壓縮後雙擊 `NTU-COOL-Downloader`。
  如果出現「無法打開，因為 Apple 無法檢查」，到 **系統設定 → 隱私權與安全性**，在下方按 **強制打開**，再雙擊一次。

### 2. 第一次使用：登入（只需做一次）

程式會自動開啟一個瀏覽器視窗（Windows 用 Edge，Mac 用 Chrome）。
**用平常登入 NTU COOL 的方式登入即可**，登入完成後視窗會自動關閉。

登入狀態會存在你自己的電腦裡，下次打開就不用再登入；過期時程式會再請你登入一次。

> Mac 需要先安裝 [Google Chrome](https://www.google.com/chrome/)。

### 3. 貼上網址

在瀏覽器打開課程，複製網址貼進程式：

- **整門課**：`https://cool.ntu.edu.tw/courses/12345` → 會列出所有影片，按 Enter 全部下載，或輸入編號如 `1,3,5-7`。
- **單一影片**：從課程的「單元 (Modules)」頁面點開影片，複製網址，例如 `https://cool.ntu.edu.tw/courses/12345/modules/items/678910`。

影片會存到 **下載 (Downloads) → NTU COOL Videos → 課程名稱** 資料夾。

## 常見問題

**找不到影片 / 顯示 0 部影片**
目前只會抓「單元 (Modules)」頁面裡的 cool-video 影片。放在公告、頁面或作業裡的影片抓不到；YouTube 等外部影片也不支援。

**找不到 Edge 或 Chrome**
請安裝 [Google Chrome](https://www.google.com/chrome/) 後再試一次。

**想換帳號 / 登出**
在命令列執行 `NTU-COOL-Downloader --logout`（或 `python ntu_cool_dl.py --logout`），會刪除儲存的登入資料。

**下載到一半中斷了**
網路中斷時程式會自動重試、從中斷處繼續。如果還是失敗，再執行一次並選同樣的影片即可。已經下載完的影片會自動略過。

**看不懂的網址錯誤**
請貼 `cool.ntu.edu.tw` 開頭的網址，不要貼影片播放器 (`cool-video.dlc.ntu.edu.tw`) 的網址。

## 進階：用 Python 執行 / 命令列

```bash
git clone https://github.com/popcorn-volcano/ntu-cool-video-downloader
cd ntu-cool-video-downloader
pip install -r requirements.txt
python ntu_cool_dl.py                                   # 互動模式
python ntu_cool_dl.py <網址> [<網址> ...] --all          # 不詢問，全部下載
python ntu_cool_dl.py <網址> --list                      # 只列出影片
python ntu_cool_dl.py <網址> -o D:\Lectures             # 指定存放資料夾
python ntu_cool_dl.py --logout                           # 刪除儲存的登入資料
```

用 Python 執行時不需要另外安裝瀏覽器元件，會直接使用電腦裡的 Edge 或 Chrome。

## 運作原理

0. 開啟 Edge / Chrome 讓使用者正常登入 NTU COOL，取得登入 cookie（存在本機）。
1. 用 NTU COOL（Canvas）API 找出課程單元裡連到 cool-video 的項目。
2. 透過 Canvas 的 `sessionless_launch` API 取得 LTI 登入表單，登入影片平台。
3. 影片平台的 `/api/courses/<c>/videos/<v>/view` 會給一個暫時有效的 MP4 下載連結，直接下載。

## 注意事項

- 本工具與臺灣大學、NTU COOL 官方無關。
- 只能下載你**有修課、本來就看得到**的影片。
- 上課影片的著作權屬於授課老師與學校。請只用於個人學習，**不要轉傳或公開分享**。

## 發布新版本（維護者）

推送 `v*` 標籤後，GitHub Actions 會自動建置 Windows / macOS 版並建立 Release：

```bash
git tag v1.3.0
git push origin v1.3.0
```

授權：[MIT](LICENSE)

---

## English

Download lecture videos from NTU COOL (the cool-video player) as MP4 files for offline study.

1. **Download** the [Windows .exe](https://github.com/popcorn-volcano/ntu-cool-video-downloader/releases/latest/download/NTU-COOL-Downloader-Windows.exe) or the [macOS .zip](https://github.com/popcorn-volcano/ntu-cool-video-downloader/releases/latest/download/NTU-COOL-Downloader-macOS.zip). Nothing else to install.
   - Windows SmartScreen warning: click **More info → Run anyway**.
   - macOS "cannot be opened": go to **System Settings → Privacy & Security → Open Anyway**.
2. **First run:** a browser window (Edge on Windows, Chrome on macOS) opens. Sign in to NTU COOL as usual and it closes by itself. Your login is saved locally, so next time you skip this. macOS needs [Google Chrome](https://www.google.com/chrome/) installed. Use `--logout` to forget the login.
3. **Paste a link:** a course link (`https://cool.ntu.edu.tw/courses/12345`) lists every video so you can pick which to download, and a module item link downloads one video.

Videos are saved to `Downloads/NTU COOL Videos/<course>/`. Dropped connections are retried automatically and interrupted downloads resume.
Only cool-video items on a course's **Modules** page are found.

Not affiliated with National Taiwan University. Only videos you can already access are downloadable. Please respect copyright and keep downloads for personal study.
