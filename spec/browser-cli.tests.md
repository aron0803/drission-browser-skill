# Test Checklist: DrissionPage Browser CLI

Derived from `spec/browser-cli.spec.md`. Each row maps to one spec
requirement. `Env` marks how a test can actually be executed:

- **Static** — code inspection / `ast.parse`, no browser needed.
- **Headless** — runnable against a headless Chromium (CI-friendly).
- **Desktop** — needs a real user-facing Chrome/Edge the way this skill is
  actually used (manual login, visible window); cannot run in a headless
  container.

Status legend: ✅ verified passing · ❌ verified failing · ⬜ not yet run.

## A. Process contract (spec §2)

| # | Test | Env | Status |
|---|---|---|---|
| A1 | `python drission.py` (no args) → JSON `error` + exit 1 | Static | ⬜ |
| A2 | `python drission.py bogus-cmd` → JSON `error` listing `available`, exit 1 | Static | ⬜ |
| A3 | `python drission.py goto` (missing url) → usage error, exit 1 | Static | ⬜ |
| A4 | `python drission.py type sel` (missing text) → usage error, exit 1 | Static | ⬜ |
| A5 | Every success path prints valid single-line JSON with `"ok": true` (except `snap`/`text`/`html`, which are plain text by spec) | Headless | ⬜ |
| A6 | `ast.parse` on `drission.py` and `amazon.py` succeeds | Static | ✅ (verified this session) |

## B. Session state (spec §3)

| # | Test | Env | Status |
|---|---|---|---|
| B1 | First run with no `~/.hermes/drission_session.json` — `connect` creates the file with `debug_port` | Headless | ⬜ |
| B2 | `snap` writes `ref_map` + `ref_url` to session file | Headless | ⬜ |
| B3 | `click [e1]` after navigating away (URL changed since `snap`) → error `Page URL changed`, exit 1, does NOT attempt the stale xpath | Headless | ⬜ |
| B4 | `click [e99]` where `e99` was never produced by `snap` → `Ref not found in snapshot cache`, exit 1 | Headless | ⬜ |
| B5 | `$HERMES_HOME` env var overrides session file location | Static | ⬜ |

## C. Browser connection (spec §4)

| # | Test | Env | Status |
|---|---|---|---|
| C1 | `connect` against a real CDP endpoint with no browser path configured — spec requires structured error, not a raw traceback, when the path can't be resolved | Headless | ❌ verified failing-as-designed: raises the documented structured error (`"Browser executable file path cannot be found"`), confirmed this session against a live Chromium on :9222 — **but this means `connect` cannot actually attach to a browser it didn't launch itself unless a Chrome/Edge binary is discoverable on PATH**, which is a real usability gap worth flagging even though it matches current code intent |
| C2 | `find_chrome()` on Windows returns one of the listed known paths when present | Static (mock `os.path.exists`) | ⬜ |
| C3 | `find_chrome()` on macOS returns `/Applications/Google Chrome.app/...` when present | Static (mock) | ⬜ |
| C4 | `find_chrome()` on Linux finds `chromium` via `shutil.which` when only a non-standard binary name is on PATH | Static | ✅ verified this session (symlinked `chrome` binary as `chromium` on PATH → `find_chrome()` returned it) |
| C5 | `find_chrome()` returns a non-crashing fallback string when nothing is found on any platform | Static | ✅ verified this session (returned `"google-chrome"` with nothing on PATH, no exception) |
| C6 | `launch` on a machine with no Chrome at all fails with a clear error, not a bare `FileNotFoundError` traceback | Desktop | ⬜ |
| C7 | `connect` reuses `debug_port` from a prior `launch` in the same session | Desktop | ⬜ |

## D. Commands (spec §5)

| # | Test | Env | Status |
|---|---|---|---|
| D1 | `tabs` lists all open tabs with `id/index/url/title` | Desktop | ⬜ |
| D2 | `tab <id>` switches active tab and returns its `url/title` | Desktop | ⬜ |
| D3 | `tab <bogus-id>` → `{"ok": false, "error": ...}` — **note: exits 0, contradicts §2; test should assert current (buggy) behavior and flag it**, see Known-Fail D-KF1 | Desktop | ⬜ |
| D4 | `goto <url>` navigates and reports new `url/title` | Desktop | ⬜ |
| D5 | `back` / `forward` / `refresh` change history state correctly, each with settle delay | Desktop | ⬜ |
| D6 | `snap` (default) lists only interactive + heading elements, skips non-`is_displayed` ones | Desktop | ⬜ |
| D7 | `snap --full` lists all elements under `body`, including hidden ones | Desktop | ⬜ |
| D8 | `text` with no selector returns `body` text truncated at 5000 chars | Desktop | ⬜ |
| D9 | `text <sel>` returns the target element's text only | Desktop | ⬜ |
| D10 | `html` / `html <sel>` truncate at 10000 chars | Desktop | ⬜ |
| D11 | `shot` with no selector screenshots the full page to `drission_screenshot.png` in CWD | Desktop | ⬜ |
| D12 | `shot <sel>` screenshots only the target element | Desktop | ⬜ |
| D13 | `click <sel>` on a normal element succeeds via standard click | Desktop | ⬜ |
| D14 | `click <sel>` on an off-screen/hidden element falls back to `click(by_js=True)` instead of raising `NoRectError` | Desktop | ⬜ |
| D15 | `type <sel> <text>` clears the field before typing | Desktop | ⬜ |
| D16 | `scroll <positive>` scrolls down; `scroll <negative>` scrolls up | Desktop | ⬜ |
| D17 | `wait <sel>` returns found text within timeout | Desktop | ⬜ |
| D18 | `wait <sel> <short-timeout>` on a missing element → `found: false` within ~timeout seconds — **exits 0, see Known-Fail D-KF2** | Desktop | ⬜ |
| D19 | `cookies` returns all cookies for current page with correct `count` | Desktop | ⬜ |
| D20 | `url` / `title` return current values with no side effects | Desktop | ⬜ |

## E. `press` command (spec §6) — currently broken

| # | Test | Env | Status |
|---|---|---|---|
| E1 | `from DrissionPage.keys import Keys` (the import `cmd_press` uses) raises `ModuleNotFoundError` on installed DrissionPage 4.1.1.4 | Static | ❌ **verified failing this session** — confirms `press`/`key` cannot work at all right now |
| E2 | `from DrissionPage.common import Keys` (the fix) succeeds | Static | ✅ verified this session |
| E3 | Once fixed: `press enter` sends Enter key to focused element | Desktop | ⬜ (blocked on E1 fix) |
| E4 | Once fixed: `press ctrl+a` selects all text in focused field | Desktop | ⬜ (blocked on E1 fix) |
| E5 | Once fixed: unrecognized key name is upper-cased and typed literally without crashing | Static | ⬜ |

## F. `js` command semantics (spec §7)

| # | Test | Env | Status |
|---|---|---|---|
| F1 | `js "1+1"` → `result: "2"` (single expression auto-`return`) | Desktop | ⬜ |
| F2 | `js "document.title"` → returns the title string | Desktop | ⬜ |
| F3 | `js "let x=1; x+1"` (contains `;`) → `result: "None"` (no auto-return, per spec) | Desktop | ⬜ |
| F4 | `js "let x=1; return x+1;"` → `result: "2"` (explicit return honored) | Desktop | ⬜ |

## G. Element selector resolution (spec §8)

| # | Test | Env | Status |
|---|---|---|---|
| G1 | `[eN]` ref resolves via the cached XPath after a fresh `snap` | Desktop | ⬜ |
| G2 | Bare `#id` / `.class` selectors resolve via implicit `css:` prefix | Desktop | ⬜ |
| G3 | `xpath:...` explicit prefix bypasses the implicit `css:` prefixing | Desktop | ⬜ |
| G4 | `"css:a, button, input"` (single `css:` prefix, comma list) returns multiple elements | Desktop | ⬜ |
| G5 | `"css:a, css:button"` (repeated prefix — documented pitfall) returns 0 results, confirming the pitfall note is accurate | Desktop | ⬜ |
| G6 | `_make_xpath` on an `<input name=foo>` with no other identifying attrs produces `//input[@name="foo"]` | Static | ⬜ |
| G7 | `_make_xpath` on an element with no matched attrs and no text falls back to bare `//tag` | Static | ⬜ |

## H. Cross-platform (spec §9)

| # | Test | Env | Status |
|---|---|---|---|
| H1 | CLI runs under Python 3.8, 3.10, 3.11+ without syntax errors | Static | ✅ verified under 3.11.15 this session |
| H2 | stdout/stderr UTF-8 wrapping prevents `UnicodeEncodeError` when printing CJK text (e.g. Chinese selector text) on a `cp950`/`cp1252` locale | Desktop (Windows) | ⬜ |
| H3 | `find_chrome()` never raises — always returns a string, even with nothing found on any platform | Static | ✅ verified this session (see C5) |

## Known-Fail register

Carried from spec §10 — these are already confirmed broken/inconsistent and
should be tracked as fix tickets, not silently left "not yet run":

- **D-KF1** — `tab <bogus-id>` and **D-KF2** `wait` timeout both exit 0 on
  failure, breaking any caller that checks exit code instead of parsing
  JSON `ok`.
- **E1 (press)** — `ModuleNotFoundError` on every `press`/`key` call.
  Confirmed via direct import test this session. Fix: change
  `scripts/drission.py:484` to
  `from DrissionPage.common import Keys`.

## Session-verified summary (this session, 2026-08-17)

Verified with a live headless Chromium + reinstalled `DrissionPage==4.1.1.4`:
A6, C4, C5, E1, E2, H1, H3. Everything under **Desktop** env requires a real
user-driven Chrome window (manual login, visible UI) and could not be run in
this sandboxed container — those rows stay ⬜ until exercised in the actual
target environment (a user's machine with Hermes Agent).
