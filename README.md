# DrissionPage Browser Skill for Hermes Agent

讓 Hermes Agent 操作**你自己的 Chrome 瀏覽器** — 你手動登入網站，agent 接手操作，不用重新認證。

## 運作原理

```
你看得見的 Chrome  ←──CDP (port 9222)──→  Agent 透過 DrissionPage 操作
   (你已登入)                                (不用重新登入)
```

透過 DrissionPage + Chrome DevTools Protocol (CDP)，agent 可以：
- 連接到你已開啟的 Chrome
- 導航、點擊、輸入、截圖
- 執行 JavaScript
- 讀取 cookies
- 你手動登入的所有網站，agent 直接沿用登入狀態

## 安裝

```bash
# 1. 安裝依賴
pip install DrissionPage

# 2. 安裝 skill
hermes skills install https://github.com/aron0803/drission-browser-skill/blob/main/SKILL.md

# 3. 啟動 Chrome（需要 remote debugging port）
# 方式 A：讓 skill 自動啟動
# （agent 會執行 python drission.py launch）

# 方式 B：手動啟動
# 先關閉所有 Chrome，然後：
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

## 使用

在 Hermes Agent 對話中直接說：
- 「幫我打開 Google 搜尋 XXX」
- 「幫我登入這個網站填表單」
- 「幫我爬這個頁面的資料」

Agent 會自動載入 skill 並操作你的瀏覽器。

## 指令參考

```bash
python drission.py connect       # 連線到 Chrome
python drission.py goto <url>    # 導航
python drission.py snap          # 擷取頁面元素
python drission.py click <sel>   # 點擊
python drission.py type <sel> <t> # 輸入
python drission.py js <code>     # 執行 JS
python drission.py cookies       # 讀取 cookies
python drission.py shot          # 截圖
```

## 需求

- Python 3.8+
- DrissionPage (`pip install DrissionPage`)
- Chrome 或 Edge 瀏覽器
- Hermes Agent
