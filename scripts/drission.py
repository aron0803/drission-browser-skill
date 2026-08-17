#!/usr/bin/env python3
"""
DrissionPage CLI — Hermes Agent browser automation skill.
Connect to your existing Chrome browser (remote debugging port 9222)
and let the agent operate web pages you've already logged into.

Usage:
  python drission.py connect              # connect to existing Chrome
  python drission.py launch               # launch new Chrome with debugging
  python drission.py goto <url>           # navigate
  python drission.py snap                 # snapshot interactive elements
  python drission.py click <sel>          # click element
  python drission.py type <sel> <text>    # type into input
  python drission.py text [sel]           # get text content
  python drission.py html [sel]           # get HTML
  python drission.py shot [sel]           # screenshot to file
  python drission.py js <code>            # execute JavaScript
  python drission.py wait <sel> [timeout] # wait for element
  python drission.py cookies              # get cookies
  python drission.py tabs                 # list tabs
  python drission.py tab <id>             # switch tab
  python drission.py scroll <px>          # scroll (positive=down, negative=up)
  python drission.py back                 # go back
  python drission.py forward              # go forward
  python drission.py refresh              # refresh page
  python drission.py press <key>          # press keyboard key
  python drission.py url                  # get current URL
  python drission.py title                # get page title
"""

import json
import os
import sys
import time
from pathlib import Path

# Force UTF-8 output — prevents UnicodeEncodeError on Windows CP950/CP1252
import io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
SESSION_FILE = HERMES_HOME / "drission_session.json"

# ── helpers ──────────────────────────────────────────────────────────

def load_session():
    if SESSION_FILE.exists():
        return json.loads(SESSION_FILE.read_text())
    return {}

def save_session(data):
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps(data, indent=2))

def get_browser(port=None):
    """Connect to an existing Chrome via CDP, using saved or provided port."""
    from DrissionPage import Chromium
    session = load_session()
    port = port or session.get("debug_port", 9222)
    try:
        browser = Chromium(port)
        save_session({"debug_port": port})  # refresh session
        return browser, port
    except Exception as e:
        print(json.dumps({
            "error": f"Cannot connect to Chrome on port {port}",
            "detail": str(e),
            "hint": "Make sure Chrome is running with --remote-debugging-port=9222. "
                    "Use 'python drission.py launch' to start it automatically, "
                    "or run: chrome.exe --remote-debugging-port=9222"
        }))
        sys.exit(1)

def find_chrome():
    """Find Chrome/Edge executable across Windows, macOS, and Linux."""
    import shutil

    if sys.platform == "win32":
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        fallback = "chrome.exe"
    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            os.path.expanduser(
                "~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            ),
        ]
        fallback = "google-chrome"
    else:
        candidates = []
        fallback = "google-chrome"

    for p in candidates:
        if os.path.exists(p):
            return p

    # Linux (and macOS/Windows fallback): search PATH for common binary names
    for name in ("google-chrome", "google-chrome-stable", "chromium-browser",
                 "chromium", "microsoft-edge", "microsoft-edge-stable"):
        found = shutil.which(name)
        if found:
            return found

    return fallback  # hope it's on PATH

def _make_xpath(el):
    """Build a resilient XPath for an element using tag + key attributes."""
    tag = el.tag.lower()
    attrs = {}

    if tag == "a":
        href = el.attr("href")
        if href:
            attrs["@href"] = href
    elif tag == "input":
        for a in ("name", "id", "type", "placeholder", "aria-label"):
            v = el.attr(a)
            if v:
                attrs[f"@{a}"] = v
    elif tag == "button":
        for a in ("name", "id", "type", "aria-label"):
            v = el.attr(a)
            if v:
                attrs[f"@{a}"] = v
    elif tag in ("select", "textarea"):
        for a in ("name", "id"):
            v = el.attr(a)
            if v:
                attrs[f"@{a}"] = v

    text = (el.text or "").strip()[:50]
    if text and not attrs:
        attrs["text()"] = text

    if attrs:
        # Build XPath with key attributes
        parts = [f"//{tag}"]
        for k, v in attrs.items():
            if k == "text()":
                parts.append(f'[contains(text(),"{v}")]')
            elif k.startswith("@"):
                parts.append(f'[{k[1:]}="{v}"]')
        xpath = "".join(parts)
    else:
        xpath = f"//{tag}"

    return xpath


def snapshot_elements(tab, full=False):
    """
    Build a text representation of the page + store element locators.
    Default: interactive elements only.
    full=True: all visible elements.

    Returns the snapshot text. Also saves ref→xpath mapping to session file.
    """
    if full:
        selector = "css:body *"
    else:
        selector = "css:a, button, input, select, textarea, form, h1, h2, h3, h4, h5, h6, iframe, [onclick], [role='button'], [role='link'], [role='tab'], summary, details"

    lines = []
    lines.append(f"URL: {tab.url}")
    lines.append(f"Title: {tab.title}")
    lines.append("")

    idx = 0
    ref_map = {}
    try:
        elements = tab.eles(selector, timeout=2)
    except Exception:
        elements = []

    for el in elements:
        try:
            tag = el.tag.lower()
            text = (el.text or "").strip()[:80]
            idx += 1
            ref = f"[e{idx}]"

            attrs = ""
            if tag == "a":
                href = el.attr("href") or ""
                attrs = f' href="{href[:100]}"'
            elif tag == "input":
                itype = el.attr("type") or "text"
                placeholder = el.attr("placeholder") or ""
                name = el.attr("name") or ""
                value = el.attr("value") or ""
                parts = []
                if itype != "text":
                    parts.append(f"type={itype}")
                if placeholder:
                    parts.append(f'placeholder="{placeholder[:40]}"')
                if name:
                    parts.append(f'name="{name}"')
                if value:
                    parts.append(f'value="{value[:40]}"')
                attrs = " " + " ".join(parts)
            elif tag == "button":
                btn_type = el.attr("type") or "button"
                name = el.attr("name") or ""
                if btn_type != "button":
                    attrs += f" type={btn_type}"
                if name:
                    attrs += f' name="{name}"'
            elif tag in ("select", "textarea"):
                name = el.attr("name") or ""
                if name:
                    attrs = f' name="{name}"'
            elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                pass  # headings just show text
            elif tag == "iframe":
                src = el.attr("src") or ""
                attrs = f' src="{src[:100]}"'

            # Visibility check — skip hidden
            if not full:
                try:
                    if not el.states.is_displayed:
                        continue
                except Exception:
                    pass

            xpath = _make_xpath(el)
            ref_map[ref] = xpath

            line = f"{ref} <{tag}>{attrs} {text}"
            lines.append(line)
        except Exception:
            continue

    # Save ref map to session
    session = load_session()
    session["ref_map"] = ref_map
    session["ref_url"] = tab.url
    save_session(session)

    lines.append("")
    lines.append(f"--- {idx} elements shown ---")
    lines.append("Use [eN] refs or CSS selectors with: click [eN], type [eN] \"text\"")
    return "\n".join(lines)


# ── commands ─────────────────────────────────────────────────────────

def cmd_connect():
    browser, port = get_browser()
    tab = browser.latest_tab
    save_session({"debug_port": port})
    print(json.dumps({
        "ok": True,
        "action": "connect",
        "port": port,
        "url": tab.url,
        "title": tab.title,
        "tabs": browser.tabs_count,
    }, ensure_ascii=False))

def cmd_launch():
    chrome_path = find_chrome()
    from DrissionPage import Chromium, ChromiumOptions
    import subprocess
    import atexit

    co = ChromiumOptions()
    co.set_local_port(9222)
    co.set_argument("--remote-debugging-port=9222")
    co.set_argument("--no-first-run")
    co.set_argument("--no-default-browser-check")
    co.set_browser_path(chrome_path)

    try:
        browser = Chromium(addr_or_opts=co)
    except Exception:
        # Chrome might not be running — launch it
        subprocess.Popen(
            [chrome_path, "--remote-debugging-port=9222", "--no-first-run",
             "--no-default-browser-check", "--new-window", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(3)
        browser = Chromium(9222)

    tab = browser.latest_tab
    save_session({"debug_port": 9222})
    print(json.dumps({
        "ok": True,
        "action": "launch",
        "port": 9222,
        "browser": chrome_path,
        "url": tab.url,
        "title": tab.title,
        "hint": "Browser launched. Log in to websites you need, then agent can operate them."
    }, ensure_ascii=False))

def cmd_goto(url):
    browser, _ = get_browser()
    tab = browser.latest_tab
    tab.get(url)
    print(json.dumps({
        "ok": True,
        "url": tab.url,
        "title": tab.title,
    }, ensure_ascii=False))

def cmd_snap(args):
    full = "--full" in args
    browser, _ = get_browser()
    tab = browser.latest_tab
    print(snapshot_elements(tab, full=full))

def cmd_click(sel):
    browser, _ = get_browser()
    tab = browser.latest_tab
    el = resolve_element(tab, sel)
    try:
        el.click()
    except Exception:
        # Fallback: JS click for elements without screen position (NoRectError, etc.)
        el.click(by_js=True)
    time.sleep(0.5)
    print(json.dumps({
        "ok": True,
        "action": "click",
        "selector": sel,
        "url": tab.url,
        "title": tab.title,
    }, ensure_ascii=False))

def cmd_type(sel, text):
    browser, _ = get_browser()
    tab = browser.latest_tab
    el = resolve_element(tab, sel)
    el.clear()
    el.input(text)
    print(json.dumps({
        "ok": True,
        "action": "type",
        "selector": sel,
        "text": text[:100],
    }, ensure_ascii=False))

def cmd_text(args):
    browser, _ = get_browser()
    tab = browser.latest_tab
    if args:
        el = resolve_element(tab, args[0])
        print(el.text)
    else:
        print(tab.ele("body").text[:5000])

def cmd_html(args):
    browser, _ = get_browser()
    tab = browser.latest_tab
    if args:
        el = resolve_element(tab, args[0])
        print(el.html[:10000])
    else:
        print(tab.html[:10000])

def cmd_shot(args):
    browser, _ = get_browser()
    tab = browser.latest_tab
    out = str(Path(__file__).resolve().parent / "drission_screenshot.png")
    if args:
        el = resolve_element(tab, args[0])
        el.screenshot(out)
    else:
        tab.get_screenshot(path=out)
    print(json.dumps({
        "ok": True,
        "file": os.path.abspath(out),
    }, ensure_ascii=False))

def cmd_js(code):
    browser, _ = get_browser()
    tab = browser.latest_tab
    # DrissionPage's run_js wraps code in function(){...}.
    # For single expressions, prepend 'return' to get the value back.
    # For multi-statement code (contains ; or newlines), leave as-is.
    stripped = code.strip()
    if "\n" not in stripped and ";" not in stripped and not stripped.startswith("return "):
        code = "return " + code
    result = tab.run_js(code)
    print(json.dumps({
        "ok": True,
        "result": str(result)[:5000],
    }, ensure_ascii=False))

def cmd_wait(sel, timeout=10):
    browser, _ = get_browser()
    tab = browser.latest_tab
    from DrissionPage.errors import ElementNotFoundError
    try:
        el = tab.ele(sel, timeout=float(timeout))
        print(json.dumps({
            "ok": True,
            "found": True,
            "text": (el.text or "")[:200],
        }, ensure_ascii=False))
    except Exception:
        print(json.dumps({
            "ok": False,
            "found": False,
            "error": f"Element '{sel}' not found after {timeout}s",
        }, ensure_ascii=False))
        sys.exit(1)

def cmd_cookies():
    browser, _ = get_browser()
    tab = browser.latest_tab
    cookies = tab.cookies()
    print(json.dumps({
        "ok": True,
        "url": tab.url,
        "cookies": cookies,
        "count": len(cookies),
    }, ensure_ascii=False))

def cmd_tabs():
    browser, _ = get_browser()
    tabs = []
    for i, t in enumerate(browser.get_tabs()):
        try:
            tabs.append({"id": t.tab_id, "index": i, "url": t.url, "title": t.title})
        except Exception:
            tabs.append({"id": t.tab_id, "index": i, "url": "?", "title": "?"})
    print(json.dumps({"ok": True, "tabs": tabs, "count": len(tabs)}, ensure_ascii=False))

def cmd_tab(tab_id):
    browser, _ = get_browser()
    for t in browser.get_tabs():
        if t.tab_id == tab_id:
            t.set.main_tab()
            print(json.dumps({
                "ok": True,
                "tab_id": t.tab_id,
                "url": t.url,
                "title": t.title,
            }, ensure_ascii=False))
            return
    print(json.dumps({"ok": False, "error": f"Tab {tab_id} not found"}))
    sys.exit(1)

def cmd_scroll(px):
    browser, _ = get_browser()
    tab = browser.latest_tab
    tab.scroll.down(int(px)) if int(px) > 0 else tab.scroll.up(abs(int(px)))
    print(json.dumps({"ok": True, "action": "scroll", "pixels": px}, ensure_ascii=False))

def cmd_back():
    browser, _ = get_browser()
    tab = browser.latest_tab
    tab.back()
    time.sleep(0.5)
    print(json.dumps({"ok": True, "url": tab.url, "title": tab.title}, ensure_ascii=False))

def cmd_forward():
    browser, _ = get_browser()
    tab = browser.latest_tab
    tab.forward()
    time.sleep(0.5)
    print(json.dumps({"ok": True, "url": tab.url, "title": tab.title}, ensure_ascii=False))

def cmd_refresh():
    browser, _ = get_browser()
    tab = browser.latest_tab
    tab.refresh()
    time.sleep(0.5)
    print(json.dumps({"ok": True, "url": tab.url, "title": tab.title}, ensure_ascii=False))

def cmd_press(key):
    from DrissionPage.common import Keys
    browser, _ = get_browser()
    tab = browser.latest_tab
    key_map = {
        "enter": "ENTER", "tab": "TAB", "escape": "ESCAPE", "esc": "ESCAPE",
        "backspace": "BACKSPACE", "delete": "DELETE", "space": "SPACE",
        "arrowup": "UP", "arrowdown": "DOWN", "arrowleft": "LEFT", "arrowright": "RIGHT",
        "up": "UP", "down": "DOWN", "left": "LEFT", "right": "RIGHT",
        "pageup": "PAGE_UP", "pagedown": "PAGE_DOWN", "home": "HOME", "end": "END",
        "f1": "F1", "f2": "F2", "f3": "F3", "f4": "F4", "f5": "F5",
        "f6": "F6", "f7": "F7", "f8": "F8", "f9": "F9", "f10": "F10",
        "f11": "F11", "f12": "F12",
        "ctrl+a": ("CTRL", "A"), "ctrl+c": ("CTRL", "C"), "ctrl+v": ("CTRL", "V"),
    }
    k = key_map.get(key.lower(), key.upper())
    if isinstance(k, tuple):
        tab.actions.key_down(k[0]).type(k[1]).key_up(k[0])
    else:
        tab.actions.type(getattr(Keys, k, key))
    print(json.dumps({"ok": True, "key": key}, ensure_ascii=False))

def cmd_url():
    browser, _ = get_browser()
    tab = browser.latest_tab
    print(json.dumps({"ok": True, "url": tab.url, "title": tab.title}, ensure_ascii=False))

def cmd_title():
    browser, _ = get_browser()
    tab = browser.latest_tab
    print(json.dumps({"ok": True, "title": tab.title}, ensure_ascii=False))


# ── element resolution ──────────────────────────────────────────────

def resolve_element(tab, sel):
    """Resolve selector: [eN] ref from snapshot, or raw CSS/XPath selector."""
    from DrissionPage.errors import ElementNotFoundError

    # Handle [eN] references from snapshot
    if sel.startswith("[e") and "]" in sel:
        session = load_session()
        ref_map = session.get("ref_map", {})
        ref_url = session.get("ref_url", "")

        if sel not in ref_map:
            print(json.dumps({
                "error": f"Ref '{sel}' not found in snapshot cache.",
                "hint": "Run 'snap' first to capture elements, or use a raw CSS selector."
            }))
            sys.exit(1)

        # Check if URL changed (refs may be stale)
        if tab.url != ref_url:
            print(json.dumps({
                "error": f"Page URL changed since snapshot. Re-run 'snap' first.",
                "old_url": ref_url,
                "current_url": tab.url,
            }))
            sys.exit(1)

        xpath = ref_map[sel]
        try:
            return tab.ele(f"xpath:{xpath}", timeout=5)
        except ElementNotFoundError:
            print(json.dumps({
                "error": f"Element '{sel}' (xpath: {xpath}) no longer on page.",
                "hint": "Page content may have changed. Re-run 'snap'."
            }))
            sys.exit(1)

    # Raw CSS selector — add 'css:' prefix for DrissionPage
    try:
        if not any(sel.startswith(p) for p in ("css:", "tag:", "xpath:", "text:", "@")):
            sel = f"css:{sel}"
        return tab.ele(sel, timeout=5)
    except ElementNotFoundError:
        print(json.dumps({
            "error": f"Element not found: '{sel}'",
            "hint": "Run 'snap' to see available elements. The page may have changed."
        }))
        sys.exit(1)


# ── main ─────────────────────────────────────────────────────────────

COMMANDS = {
    "connect": lambda args: cmd_connect(),
    "launch": lambda args: cmd_launch(),
    "goto": lambda args: cmd_goto(args[0]) if args else _usage(),
    "snap": lambda args: cmd_snap(args),
    "snapshot": lambda args: cmd_snap(args),
    "click": lambda args: cmd_click(args[0]) if args else _usage(),
    "type": lambda args: cmd_type(args[0], " ".join(args[1:])) if len(args) >= 2 else _usage(),
    "input": lambda args: cmd_type(args[0], " ".join(args[1:])) if len(args) >= 2 else _usage(),
    "text": lambda args: cmd_text(args),
    "html": lambda args: cmd_html(args),
    "shot": lambda args: cmd_shot(args),
    "screenshot": lambda args: cmd_shot(args),
    "js": lambda args: cmd_js(" ".join(args)) if args else _usage(),
    "wait": lambda args: cmd_wait(args[0], args[1] if len(args) > 1 else 10) if args else _usage(),
    "cookies": lambda args: cmd_cookies(),
    "tabs": lambda args: cmd_tabs(),
    "tab": lambda args: cmd_tab(args[0]) if args else _usage(),
    "scroll": lambda args: cmd_scroll(args[0]) if args else _usage(),
    "back": lambda args: cmd_back(),
    "forward": lambda args: cmd_forward(),
    "refresh": lambda args: cmd_refresh(),
    "reload": lambda args: cmd_refresh(),
    "press": lambda args: cmd_press(args[0]) if args else _usage(),
    "key": lambda args: cmd_press(args[0]) if args else _usage(),
    "url": lambda args: cmd_url(),
    "title": lambda args: cmd_title(),
}

def _usage():
    print(json.dumps({"error": "Missing arguments", "usage": __doc__}))
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        _usage()

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]

    if cmd in COMMANDS:
        COMMANDS[cmd](args)
    else:
        print(json.dumps({
            "error": f"Unknown command: '{cmd}'",
            "available": sorted(COMMANDS.keys()),
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()
