---
name: drission-browser
description: "Use when the user wants to browse the web, open websites, search online, look up information, find products, fill forms, or interact with any web page (瀏覽網頁、打開網站、搜尋、查資料、找東西、填表單、網頁操作). Connects to the user's existing Chrome/Edge via CDP — no re-login needed. Covers: 網路, 網頁, 查, 找, 搜, 開, 登入, 填, 點, 輸入, 爬, Amazon, Google, Gmail, and any website interaction."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [browser, automation, drissionpage, cdp, chrome]
    related_skills: []
---

# DrissionPage Browser Skill

Operate a **real Chrome/Edge browser** through DrissionPage + CDP (Chrome DevTools Protocol). The user opens their browser, logs into websites manually, then the agent connects and takes over — no re-authentication needed.

## Overview

This skill wraps DrissionPage (a Python browser automation library) as a CLI tool that the agent calls via `terminal()`. It connects to the user's existing Chrome/Edge instance through the remote debugging protocol (port 9222), so all cookies, sessions, and login state are preserved.

Key advantages over Hermes's built-in browser tools:
- **Pre-authenticated** — user logs in once, agent reuses the same browser session
- **Stealth-capable** — DrissionPage has built-in anti-detection features
- **Network monitoring** — can intercept and inspect HTTP requests
- **Full DOM access** — iframe, shadow DOM, file downloads all supported
- **Visible operation** — user can watch the agent work in their real browser

## When to Use

- The user says "help me fill out this form" or "book this for me"
- Web scraping / data extraction from authenticated pages
- Automating multi-step web workflows (booking, checkout, form submission)
- Interacting with sites that require login (banking, admin panels, dashboards)
- Reverse engineering web apps (monitor network requests, inspect JS behavior)
- Any time the built-in `browser` tools would work but the user wants to use their own logged-in browser

Don't use for: simple GET requests (use `curl`), pages that don't need authentication, or when the built-in browser tools are sufficient.

## CLI Quick Reference

All commands are run via: `python <skill_dir>/scripts/drission.py <command> [args]`

### Lifecycle
```
launch                    Start Chrome with remote debugging enabled (port 9222)
connect                   Connect to an already-running Chrome on port 9222
tabs                      List all open tabs
tab <tab_id>              Switch to a specific tab
```

### Navigation
```
goto <url>                Navigate to a URL
back / forward            Browser history navigation
refresh                   Reload the current page
url                       Show current URL
title                     Show page title
```

### Page Inspection
```
snap                      Snapshot interactive elements (a, button, input, select, textarea + headings)
snap --full               Full DOM snapshot (all visible elements)
text [selector]           Get text content of element or entire page
html [selector]           Get inner HTML of element or entire page
shot [selector]           Screenshot page or element → drission_screenshot.png
```

### Interaction
```
click <sel>               Click an element ([eN] ref or CSS selector)
type <sel> <text>         Clear and type into an input field
press <key>               Press a keyboard key (enter, tab, escape, space, etc.)
scroll <px>               Scroll by N pixels (positive=down, negative=up)
wait <sel> [seconds]      Wait for element to appear (default 10s)
```

### Advanced
```
js <code>                 Execute JavaScript and get result
cookies                   Get all cookies for current page
```

### Amazon Price Scraper (amazon.py)

A helper script for Amazon product searches with verified detail-page prices:

```bash
python amazon.py search "ryzen ai max+ 395 128gb"    # search and list
python amazon.py search "max 395" --min-ram 128       # filter by min RAM
python amazon.py search "max 395" --detail             # also drill into each
python amazon.py detail B0H12525JZ                     # drill one product
```

Handles Amazon edge cases: "cannot ship" buybox (extracts real price from variant JSON), dynamic pricing, and buybox text regex fallback.

## Workflow: First-Time Setup

Before the agent can use this skill for the first time:

1. **Install DrissionPage** (one-time):
   ```bash
   pip install DrissionPage
   ```

2. **Launch Chrome with debugging** — two options:
   - **Let the skill launch it:** `python drission.py launch` (opens a fresh Chrome window)
   - **Manual:** Close all Chrome windows, then run:
     ```bash
     "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
     ```

3. **User logs in** — the user manually logs into the websites they need in that Chrome window.

4. **Agent connects** — `python drission.py connect` to verify the connection works.

The session file (`~/.hermes/drission_session.json`) tracks the debug port and element references across calls.

## Workflow: Typical Agent Session

```
1. connect            — Verify browser is reachable
2. tabs               — See what's already open
3. tab <id>           — Switch to the right tab (or goto <url>)
4. snap               — See what's on the page (interactive elements with [eN] refs)
5. click [e5]         — Click a button
6. type [e3] "hello"  — Type into a field
7. snap               — Re-snapshot to see updated page state
8. click [e7]         — Continue interacting
```

**IMPORTANT:** Always run `snap` before using `[eN]` references. After any interaction that changes the page (click, goto, form submit), re-run `snap` to get fresh references.

## Element Selectors

Two selector types are supported:

1. **[eN] references** — from `snap` output, e.g. `[e5]`. These use cached XPath lookups. They only work on the SAME page URL that was snapshotted. After navigation or DOM changes, re-run `snap`.

2. **CSS selectors** — standard CSS, e.g. `#login-btn`, `.search-input`, `button[type='submit']`, `a[href='/dashboard']`

3. **XPath** (for direct use only, not via [eN]): prefix with `xpath:`, e.g. `xpath://button[@name='login']`

## Snapshot Output Format

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

## Common Pitfalls

1. **"[eN] ref not found" error** — Always run `snap` right before using [eN] references. Page changes invalidate cached refs. Also: piping `snap` through `head`/`grep` in the same terminal call won't affect the session file — the ref_map is saved to disk during `snap`, independent of stdout.

2. **"Cannot connect to Chrome on port 9222"** — Chrome isn't running with remote debugging. Run `launch` or start Chrome manually with `--remote-debugging-port=9222`. Close ALL existing Chrome windows first (Chrome only allows one remote debugging instance).

3. **Element not found** — The page may not have finished loading. Use `wait <sel>` before interacting, or try a different selector. CSS attribute selectors with special chars (e.g. `a[href*='AccountChooser']`) may fail — try simpler selectors or XPath instead.

4. **Typing doesn't work** — Some modern web apps use JS frameworks that need a click first to focus the field. Do: `click <sel>` then `type <sel> <text>`.

5. **Button click fails with "NoRectError"** — Element has no screen position (hidden/off-screen). The CLI now auto-falls-back to `click(by_js=True)`. If it still fails, use `js "document.querySelector('...').click()"` directly.

6. **Multi-statement JS fails** — `cmd_js` only auto-prepends `return` for single expressions. For multi-statement code (containing `;` or newlines), write it without relying on auto-return. The result will be `None` for multi-statement blocks — use a final `return` statement if you need a value.

7. **`text:` selector matches wrong element** — `tab.ele('text:Create repository')` may match a `<span>` inside a `<button>` instead of the button itself. For clickable elements, prefer CSS selectors (`button[type='submit']`) or XPath with `contains(text(),...)`.

8. **Chrome won't start with debugging port** — Close ALL Chrome processes first:
   ```bash
   taskkill /F /IM chrome.exe 2>/dev/null
   ```
   Then launch again.

9. **DrissionPage `eles()` selector format** — Use a single `css:` prefix at the start: `"css:a, button, input"` works. `"css:a, css:button, css:input"` returns 0 results. Same for `ele()`: `"css:#id"` or just `"#id"` (bare strings do text-matching, not CSS).

10. **`press` command imports** — Do NOT use `from DrissionPage.keys import Keys` (that module doesn't exist in 4.x). Use `from DrissionPage.common import Keys` or access via `tab.actions.type(Keys.ENTER)`.

11. **Multi-statement JS returns None** — `run_js` wraps code in `function(){return <code>}`. Multi-statement code (containing `;` or newlines) needs an explicit `return` statement at the end to get a value back.

12. **Amazon price traps** — When `snap` or `extract_detail` returns the wrong price: (a) check if buybox says "無法配送" → Amazon is showing a different item's price; extract the real price from page-source variant JSON instead. (b) All `.a-price` blocks may be `visible=False` on variant-heavy pages — check visibility before trusting a price. (c) Some prices render as bare text outside `.a-offscreen` → regex-fallback on buybox text.

## Verification Checklist

- [ ] DrissionPage installed: `python -c "from DrissionPage import Chromium; print('OK')"`
- [ ] Chrome running with `--remote-debugging-port=9222`
- [ ] `python drission.py connect` returns `{"ok": true}`
- [ ] `python drission.py snap` shows page elements
- [ ] `python drission.py click` works on an element
- [ ] `python drission.py type` works on an input field

## References

- `references/drissionpage-quirks.md` — DrissionPage 4.x API gotchas: selector formats, tab API, JS execution, click fallback patterns, visibility checks. Load when debugging selector/API issues.
