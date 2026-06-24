# DrissionPage Browser Skill for Hermes Agent

> Let your AI agent control **your own Chrome browser** — you log in manually, the agent takes over. No re-authentication needed.
>
> 讓 Hermes Agent 操作**你自己的 Chrome 瀏覽器** — 你手動登入，agent 接手，不用重新認證。

[![Skill Type](https://img.shields.io/badge/Hermes-Skill-blue)](https://hermes-agent.nousresearch.com)
[![Python](https://img.shields.io/badge/python-3.8%2B-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)

---

## ⚠️ Security Warning / 安全警告

> **Once you log into a website, the AI agent can do anything you can do in that browser.**
> This includes — but is not limited to — reading emails, sending messages, making purchases, transferring money, changing passwords, deleting accounts, and accessing private data.
>
> **一但你登入網站，AI Agent 就能在瀏覽器裡做任何你能做的事。**
> 包含但不限於：讀取郵件、發送訊息、購物下單、轉帳匯款、修改密碼、刪除帳號、存取私人資料。
>
> - ✅ **DO** let the agent browse public pages, search products, fill harmless forms
> - ✅ **允許** agent 瀏覽公開頁面、搜尋商品、填寫無害表單
> - ❌ **DO NOT** let the agent operate while logged into banking, email with sensitive data, or admin panels unless you are watching
> - ❌ **不要** 在登入網銀、含敏感資料的信箱、或管理後台時讓 agent 自行操作（除非你全程盯著）
> - 👀 **Always supervise** when the agent is working on authenticated sites
> - 👀 **全程監督** agent 在已登入網站上的操作
> - 🔒 **Close the debugging port** (or close Chrome) when you're done to prevent unauthorized access
> - 🔒 用完**關閉除錯埠**（或關閉 Chrome），防止未授權存取
>
> **Use at your own risk. The author assumes no liability for any damages.**
> **使用風險自負，作者不承擔任何損害賠償責任。**

---

## How It Works / 運作原理

```
Your visible Chrome  <-- CDP (port 9222) -->  Agent controls via DrissionPage
   (you logged in)                               (no re-login needed)
```

This skill connects Hermes Agent to your **existing Chrome/Edge browser** through the [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/) (CDP) using [DrissionPage](https://github.com/g1879/DrissionPage), a powerful Python browser automation library.

You manually log into any website once — banking, email, admin panels, dashboards — and the agent reuses your authenticated session for automation, scraping, form filling, and more.

### Why DrissionPage over Selenium/Playwright?

| Feature | DrissionPage | Selenium | Playwright |
|---------|:-----------:|:--------:|:----------:|
| Connect to existing browser | ✅ Yes | ❌ No | ✅ (limited) |
| No re-authentication | ✅ | ❌ | ❌ |
| Stealth / anti-detection | ✅ Built-in | ❌ | ❌ |
| Network request monitoring | ✅ | ❌ | ✅ |
| iframe & shadow DOM | ✅ Native | ⚠️ | ✅ |
| File download handling | ✅ | ⚠️ | ✅ |
| Lightweight (no WebDriver) | ✅ | ❌ | ❌ |

---

## Installation / 安裝

### 1. Install the skill

```bash
hermes skills install https://github.com/aron0803/drission-browser-skill/blob/main/SKILL.md
```

### 2. Install dependency

```bash
pip install DrissionPage
```

### 3. Launch Chrome with remote debugging

**Option A — Let the agent launch it** (recommended):

The agent will run `python drission.py launch` automatically.

**Option B — Manual launch:**

Close ALL Chrome windows first, then:

```bash
# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222

# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222
```

Or use **Edge**:
```bash
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222
```

---

## Usage / 使用方式

Just talk to Hermes naturally:

> "Help me check my Gmail for important emails"
>
> "Log into this admin panel and export the monthly report"
>
> "幫我打開 Google 搜尋 XXX"
>
> "幫我爬這個頁面的資料"

The agent loads the skill automatically and operates your browser.

---

## CLI Reference / 指令參考

All commands via: `python scripts/drission.py <command> [args]`

### Lifecycle / 生命週期

| Command | Description |
|---------|-------------|
| `launch` | Start Chrome with remote debugging |
| `connect` | Connect to running Chrome on port 9222 |
| `tabs` | List all open tabs |
| `tab <id>` | Switch to a specific tab |

### Navigation / 導航

| Command | Description |
|---------|-------------|
| `goto <url>` | Navigate to URL |
| `back` / `forward` | Browser history |
| `refresh` | Reload current page |
| `url` / `title` | Show current URL / title |

### Page Inspection / 頁面檢查

| Command | Description |
|---------|-------------|
| `snap` | Snapshot interactive elements (with `[eN]` refs) |
| `snap --full` | Full DOM snapshot |
| `text [sel]` | Get text content |
| `html [sel]` | Get inner HTML |
| `shot [sel]` | Screenshot page or element |

### Interaction / 互動

| Command | Description |
|---------|-------------|
| `click <sel>` | Click element (`[eN]` ref or CSS selector) |
| `type <sel> <text>` | Clear and type into input |
| `press <key>` | Press key (enter, tab, escape, space, etc.) |
| `scroll <px>` | Scroll by pixels (+down, -up) |
| `wait <sel> [s]` | Wait for element (default 10s) |

### Advanced / 進階

| Command | Description |
|---------|-------------|
| `js <code>` | Execute JavaScript and get result |
| `cookies` | Get all cookies for current page |

---

## Snapshot Format / 頁面擷取格式

```
URL: https://example.com
Title: Example Page

[e1] <h1> Welcome
[e2] <a href="/login"> Login
[e3] <input type=text placeholder="Username" name="user">
[e4] <input type=password placeholder="Password" name="pass">
[e5] <button type=submit> Sign In

--- 5 elements shown ---
Use [eN] refs or CSS selectors with: click [eN], type [eN] "text"
```

Elements are referenced by `[eN]` IDs (cached XPath) **or** standard CSS selectors (`#id`, `.class`, `button[type='submit']`).

> Always re-run `snap` after page changes — `[eN]` refs become stale after navigation.

---

## Requirements / 需求

- **Python** 3.8+
- **DrissionPage** >= 4.0 (`pip install DrissionPage`)
- **Chrome** or **Edge** browser
- **Hermes Agent** ([install guide](https://hermes-agent.nousresearch.com))

---

## Troubleshooting / 疑難排解

| Problem | Solution |
|---------|----------|
| "Cannot connect to Chrome on port 9222" | Chrome isn't running with `--remote-debugging-port=9222`. Close ALL Chrome windows and re-launch. |
| "Element not found" | Page may still be loading. Use `wait <sel>` before interacting. |
| [eN] ref broken after click | Re-run `snap` — refs are cached per page URL. |
| Typing doesn't work on some sites | Click the field first, then type: `click <sel>` then `type <sel> <text>`. |

---

## License

MIT — use freely, modify, share.

---

**Built with** [DrissionPage](https://github.com/g1879/DrissionPage) • **For** [Hermes Agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com)
