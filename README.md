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

### 2. 第一次使用：設定存取權杖（只需做一次）

程式需要一組「存取權杖 (Access Token)」，才能以你的身分讀取課程。第一次打開時程式會自動開啟設定頁面：

1. 登入 NTU COOL。
2. 在設定頁面往下找到 **已核准的整合 (Approved Integrations)**，按 **+ 新增存取權杖 (+ New Access Token)**。
3. 「用途」隨便填（例如 `video`），到期日可以留空，按 **產生權杖**。
4. 複製那一長串權杖，貼回程式視窗，按 Enter。

權杖會存在你自己的電腦裡，之後就不用再輸入。

> ⚠️ 權杖等同你的 NTU COOL 帳號權限，**不要分享給別人**。不用了可以在同一個設定頁面刪除。

### 3. 貼上網址

在瀏覽器打開課程，複製網址貼進程式：

- **整門課**：`https://cool.ntu.edu.tw/courses/12345` → 會列出所有影片，按 Enter 全部下載，或輸入編號如 `1,3,5-7`。
- **單一影片**：從課程的「單元 (Modules)」頁面點開影片，複製網址，例如 `https://cool.ntu.edu.tw/courses/12345/modules/items/678910`。

影片會存到 **下載 (Downloads) → NTU COOL Videos → 課程名稱** 資料夾。

## 常見問題

**找不到影片 / 顯示 0 部影片**
目前只會抓「單元 (Modules)」頁面裡的 cool-video 影片。放在公告、頁面或作業裡的影片抓不到；YouTube 等外部影片也不支援。

**權杖無效或已過期**
重新打開程式，它會請你貼新的權杖。也可以在命令列執行 `--forget-token` 清除舊的權杖。

**下載到一半中斷了**
再執行一次、選同樣的影片即可，會從中斷的地方繼續。已經下載完的影片會自動略過。

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
python ntu_cool_dl.py --forget-token                     # 刪除已儲存的權杖
```

也可以用環境變數 `NTU_COOL_TOKEN` 或 `--token` 提供權杖。

## 運作原理

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
git tag v1.2.0
git push origin v1.2.0
```

授權：[MIT](LICENSE)

---

## English

Download lecture videos from NTU COOL (the cool-video player) as MP4 files for offline study.

1. **Download** the [Windows .exe](https://github.com/popcorn-volcano/ntu-cool-video-downloader/releases/latest/download/NTU-COOL-Downloader-Windows.exe) or the [macOS .zip](https://github.com/popcorn-volcano/ntu-cool-video-downloader/releases/latest/download/NTU-COOL-Downloader-macOS.zip). Nothing else to install.
   - Windows SmartScreen warning: click **More info → Run anyway**.
   - macOS "cannot be opened": go to **System Settings → Privacy & Security → Open Anyway**.
2. **First run:** the app opens your NTU COOL settings page. Under **Approved Integrations**, click **+ New Access Token**, generate one, and paste it into the app. It's saved locally, so you only do this once. Keep it private.
3. **Paste a link:** a course link (`https://cool.ntu.edu.tw/courses/12345`) lists every video so you can pick which to download, and a module item link downloads one video.

Videos are saved to `Downloads/NTU COOL Videos/<course>/`. Interrupted downloads resume on the next run.
Only cool-video items on a course's **Modules** page are found.

Not affiliated with National Taiwan University. Only videos you can already access are downloadable. Please respect copyright and keep downloads for personal study.
