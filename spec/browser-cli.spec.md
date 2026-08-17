# Spec: DrissionPage Browser CLI

Formal behavior spec for `scripts/drission.py`, the CLI an agent drives via
`terminal()` to control a user's existing Chrome/Edge browser over CDP.
Derived from the current implementation + `SKILL.md` + `README.md`, with
known defects called out explicitly (see "Known deviations").

This is the source of truth for `spec/browser-cli.tests.md`. If behavior
changes, update this file first, then the test checklist.

## 1. Scope

In scope: process invocation contract, session persistence, all commands
listed in section 4, element-selector resolution, error-output shape.

Out of scope: `scripts/amazon.py` (separate helper, not covered by this
spec), the Hermes Agent runtime itself, DrissionPage's internal CDP
implementation.

## 2. Process contract

- Invocation: `python scripts/drission.py <command> [args...]`
- Every command prints **exactly one line** to stdout on success: either a
  JSON object or (for `snap`) a plain-text snapshot block.
- On success, JSON output MUST include `"ok": true`.
- On failure, the process:
  - prints a JSON object containing an `"error"` key (no `"ok"` key, or
    `"ok": false`)
  - exits with a non-zero status code
  - MAY include a `"hint"` key with a remediation suggestion
- Commands never prompt for input; all arguments come from `argv`.
- Unknown command → JSON `{"error": "Unknown command: '<cmd>'", "available": [...]}`, exit 1.
- Missing required args → JSON `{"error": "Missing arguments", "usage": <docstring>}`, exit 1.

## 3. Session state

- Session file path: `$HERMES_HOME/drission_session.json`, default
  `~/.hermes/drission_session.json`.
- Fields persisted across invocations:
  - `debug_port` (int) — CDP port to reconnect to. Set by `connect`/`launch`,
    read by every other command via `get_browser()`.
  - `ref_map` (object) — `{"[eN]": "<xpath>"}`, written by `snap`.
  - `ref_url` (string) — the page URL `snap` was run against; used to
    invalidate `ref_map` after navigation.
- Every command that touches the browser calls `get_browser()`, which reads
  `debug_port` from the session file (default 9222 if absent/missing).
- **Requirement:** a `[eN]` ref MUST NOT resolve successfully if
  `tab.url != ref_url` at resolution time — the CLI must fail closed with a
  "Page URL changed" error rather than silently resolving against a stale
  DOM.

## 4. Browser connection (`get_browser`, `find_chrome`)

- `get_browser(port=None)`:
  - Resolves port: explicit arg > session file `debug_port` > `9222`.
  - Calls `DrissionPage.Chromium(port)`.
  - On success: persists `debug_port` to session, returns `(browser, port)`.
  - On failure: prints structured error JSON (see §2) and `sys.exit(1)`.
    MUST NOT raise an uncaught traceback to stdout.
- `find_chrome()` MUST resolve a usable browser executable path on all three
  target platforms:
  - **Windows:** known install paths under `Program Files` /
    `Program Files (x86)` / `%LOCALAPPDATA%`, for both Chrome and Edge.
  - **macOS:** `/Applications/Google Chrome.app/...`,
    `/Applications/Microsoft Edge.app/...`, `/Applications/Chromium.app/...`,
    and the per-user `~/Applications/...` equivalent.
  - **Linux:** PATH lookup for `google-chrome`, `google-chrome-stable`,
    `chromium-browser`, `chromium`, `microsoft-edge`,
    `microsoft-edge-stable`.
  - If nothing is found, return a bare command name as a last-resort
    fallback (`chrome.exe` on Windows, `google-chrome` elsewhere) — this
    path exists so `subprocess.Popen` at least produces a clear
    `FileNotFoundError` instead of `find_chrome()` itself raising.
- `launch`:
  - Resolves `chrome_path` via `find_chrome()`.
  - Attempts `Chromium(addr_or_opts=co)` with `--remote-debugging-port=9222`,
    `--no-first-run`, `--no-default-browser-check`.
  - On failure, falls back to `subprocess.Popen([chrome_path, ...])` +
    3s sleep + `Chromium(9222)`.
  - On success: persists `debug_port=9222`, prints
    `{"ok": true, "action": "launch", "port": 9222, "browser": <path>, "url", "title", "hint"}`.

## 5. Commands

Every row: name → required args → success JSON shape (fields beyond `ok`) →
notable failure modes.

| Command | Args | Success fields | Notes |
|---|---|---|---|
| `connect` | — | `port, url, title, tabs` | Connects to existing browser on saved/default port. |
| `launch` | — | `port, browser, url, title, hint` | See §4. |
| `tabs` | — | `tabs: [{id, index, url, title}], count` | |
| `tab` | `<tab_id>` | `tab_id, url, title` | `{"ok": false, "error": ...}` (no exit) if id not found — **inconsistent with §2**, see Known deviations. |
| `goto` | `<url>` | `url, title` | |
| `back` / `forward` / `refresh` | — | `url, title` | 0.5s settle delay after action. |
| `url` / `title` | — | `url, title` resp. `title` | |
| `snap` | `[--full]` | plain text block (not JSON) | Writes `ref_map`/`ref_url` to session as a side effect. Default selector: interactive elements only (`a, button, input, select, textarea, form, h1-h6, iframe, [onclick], [role=button\|link\|tab], summary, details`), filtered to `is_displayed`. `--full`: all elements under `body`, unfiltered. |
| `text` | `[sel]` | plain text | No selector = `body` text, truncated to 5000 chars. |
| `html` | `[sel]` | plain text | No selector = full page HTML, truncated to 10000 chars. |
| `shot` | `[sel]` | `file` (absolute path) | Writes `drission_screenshot.png` to **current working directory**, not the skill directory. |
| `click` | `<sel>` | `action, selector, url, title` | Falls back to `click(by_js=True)` on any exception from the normal click. 0.5s settle delay. |
| `type` / `input` | `<sel> <text...>` | `action, selector, text` (truncated 100 chars) | Clears field before typing. Remaining args joined with spaces as text. |
| `press` / `key` | `<key>` | `key` | Maps common key names (see §6). |
| `scroll` | `<px>` | `action, pixels` | Positive = down, negative = up. |
| `wait` | `<sel> [timeout=10]` | `found, text` on success; `found: false, error` (no exit) on timeout | **Inconsistent with §2**: never sets non-zero exit even on "not found". |
| `js` | `<code...>` | `result` (str, truncated 5000 chars) | See §7 for return-value semantics. |
| `cookies` | — | `url, cookies, count` | |

## 6. Key mapping (`press`)

Recognized (case-insensitive) key names: `enter, tab, escape/esc, backspace,
delete, space, arrowup/up, arrowdown/down, arrowleft/left, arrowright/right,
pageup, pagedown, home, end, f1–f12, ctrl+a, ctrl+c, ctrl+v`. Anything else
is upper-cased and looked up on `DrissionPage`'s `Keys` class; if not found,
the raw string is typed literally.

## 7. JavaScript execution semantics (`js`)

- Input code is wrapped by DrissionPage as `function(){ <code> }`.
- If the trimmed input contains no `;` and no newline and doesn't already
  start with `return `, the CLI prepends `return ` so single-expression
  input yields its value.
- Multi-statement input (contains `;` or a newline) is passed through
  unmodified — the caller must supply their own trailing `return` to get a
  value back; otherwise `result` is `"None"`.

## 8. Element selector resolution (`resolve_element`)

Given a selector string:

1. **`[eN]` ref** (starts with `[e`, contains `]`):
   - Look up in session `ref_map`. Missing → error, exit 1.
   - Compare current `tab.url` to session `ref_url`. Mismatch → error
     (`Page URL changed`), exit 1.
   - Resolve the stored XPath via `tab.ele("xpath:...", timeout=5)`.
     Not found → error, exit 1.
2. **Raw selector**: if it doesn't already start with `css:`, `tag:`,
   `xpath:`, `text:`, or `@`, prefix with `css:`. Resolve via
   `tab.ele(sel, timeout=5)`. Not found → error, exit 1.

`[eN]` XPath construction (`_make_xpath`) prefers, per tag:
- `a` → `@href`
- `input` → `@name`, `@id`, `@type`, `@placeholder`, `@aria-label` (first non-empty wins per DrissionPage's attribute merge order)
- `button` → `@name`, `@id`, `@type`, `@aria-label`
- `select`/`textarea` → `@name`, `@id`
- fallback: first 50 chars of trimmed text via `contains(text(), ...)`
- fallback: bare tag XPath (`//tag`) if nothing else matched

## 9. Cross-platform requirements

- Must run under Python 3.8+ on Windows, macOS, and Linux.
- stdout/stderr are wrapped as UTF-8 `TextIOWrapper` to avoid
  `UnicodeEncodeError` on Windows code pages (cp950/cp1252).
- `find_chrome()` must not assume Windows-only paths (§4).

## 10. Known deviations from this spec (as of current `main`)

These are documented so the test checklist can mark them as **known-fail**
rather than silently passing a broken implementation:

1. ~~**`press` is broken on all platforms.**~~ **Fixed.** `cmd_press`
   previously did `from DrissionPage.keys import Keys`, but DrissionPage 4.x
   has no `DrissionPage.keys` module (confirmed: `ModuleNotFoundError`). It
   now imports `from DrissionPage.common import Keys`, per SKILL.md's own
   documented pitfall #10. Verified via a mocked-tab unit test — see
   `spec/browser-cli.tests.md` E1/E1-fix/E2–E5.
2. **`tab` and `wait` don't follow the exit-code contract.** Both print
   `{"ok": false, "error": ...}` on failure but exit 0, so a caller checking
   only the exit code will treat a failed lookup/timeout as success.
3. **`shot` writes relative to CWD, not the skill directory** — if the
   agent's terminal CWD differs between calls, screenshots can land in
   unexpected places even though the reported `file` path is absolute at
   write time.
