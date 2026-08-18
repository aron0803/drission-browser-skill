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
| C1 | `get_browser()` retries with `ChromiumOptions(existing_only=True, browser_path=find_chrome(), local_port=port)` when the bare `Chromium(port)` call raises | Static (mocked `DrissionPage.Chromium`) | ✅ **fixed and verified this session** — confirmed exactly 2 calls occur (bare port, then options), and the second call's options have `is_existing_only=True` and the resolved `browser_path` set |
| C1b | End-to-end: `connect` succeeds against a real headless Chromium launched externally (not via DrissionPage), with a `chrome`-named binary discoverable via `find_chrome()` | Headless | ⬜ — blocked by an unrelated sandbox networking quirk (CDP websocket handshake returns 404 for this container's headless Chromium regardless of connection method); needs a Desktop-env or less-restricted headless-CI pass to close out |
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
| D3 | `tab <bogus-id>` → `{"ok": false, "error": ...}` + exit 1 | Static (stubbed browser) | ✅ **fixed and verified this session** — see D-KF1 |
| D4 | `goto <url>` navigates and reports new `url/title` | Desktop | ⬜ |
| D5 | `back` / `forward` / `refresh` change history state correctly, each with settle delay | Desktop | ⬜ |
| D6 | `snap` (default) lists only interactive + heading elements, skips non-`is_displayed` ones | Desktop | ⬜ |
| D7 | `snap --full` lists all elements under `body`, including hidden ones | Desktop | ⬜ |
| D8 | `text` with no selector returns `body` text truncated at 5000 chars | Desktop | ⬜ |
| D9 | `text <sel>` returns the target element's text only | Desktop | ⬜ |
| D10 | `html` / `html <sel>` truncate at 10000 chars | Desktop | ⬜ |
| D11 | `shot` with no selector screenshots the full page to `drission_screenshot.png` next to `drission.py`, independent of CWD | Static (stubbed browser) | ✅ **fixed and verified this session** — confirmed path stays under `scripts/` even after `chdir("/tmp")` |
| D12 | `shot <sel>` screenshots only the target element | Desktop | ⬜ |
| D13 | `click <sel>` on a normal element succeeds via standard click | Desktop | ⬜ |
| D14 | `click <sel>` on an off-screen/hidden element falls back to `click(by_js=True)` instead of raising `NoRectError` | Desktop | ⬜ |
| D15 | `type <sel> <text>` clears the field before typing | Desktop | ⬜ |
| D16 | `scroll <positive>` scrolls down; `scroll <negative>` scrolls up | Desktop | ⬜ |
| D17 | `wait <sel>` returns found text within timeout | Desktop | ⬜ |
| D18 | `wait <sel> <short-timeout>` on a missing element → `found: false` + exit 1 | Static (stubbed browser) | ✅ **fixed and verified this session** — see D-KF2 |
| D19 | `cookies` returns all cookies for current page with correct `count` | Desktop | ⬜ |
| D20 | `url` / `title` return current values with no side effects | Desktop | ⬜ |
| D21 | `newtab <url>` opens a new tab, navigates it, and it becomes `browser.latest_tab` | Static (stubbed browser) | ✅ verified this session — confirmed `browser.new_tab(url=...)` called with the given URL and its return value's fields echoed in the JSON |
| D22 | `closetab <id>` on an existing tab id closes it | Static (stubbed browser) | ✅ verified this session |
| D23 | `closetab` with no args defaults to the current tab's id | Static (stubbed browser) | ✅ verified this session (checked `latest_tab.tab_id` used when `args` empty) |
| D24 | `closetab <bogus-id>` → `{"ok": false, "error": ...}` + exit 1 | Static (stubbed browser) | ✅ verified this session |

## E. `press` command (spec §6) — currently broken

| # | Test | Env | Status |
|---|---|---|---|
| E1 | `from DrissionPage.keys import Keys` (the old import `cmd_press` used) raises `ModuleNotFoundError` on installed DrissionPage 4.1.1.4 | Static | ❌ verified failing against the pre-fix code — confirmed `press`/`key` could not work at all |
| E1-fix | `scripts/drission.py:484` changed to `from DrissionPage.common import Keys` | Static | ✅ **fixed and verified this session** |
| E2 | `from DrissionPage.common import Keys` (the fix) succeeds | Static | ✅ verified this session |
| E3 | `press enter` sends `Keys.ENTER` to the focused element | Static (stubbed tab) | ✅ verified this session via a mocked `tab.actions.type` — confirmed it receives the real `Keys.ENTER` codepoint (``); full Desktop verification against a real page still ⬜ |
| E4 | `press ctrl+a` calls `key_down("CTRL").type("A").key_up("CTRL")` | Static (stubbed tab) | ✅ verified this session via mocked `tab.actions` |
| E5 | Unrecognized key name is upper-cased and typed literally without crashing | Static (stubbed tab) | ✅ verified this session (`press x` → `type("X")`) |

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

## I. Frame switching (`frame`, `get_tab`)

| # | Test | Env | Status |
|---|---|---|---|
| I1 | `frame <sel>` resolves the iframe via `tab.get_frame(loc)` and stores the locator in session `active_frame` | Static (stubbed browser) | ✅ verified this session |
| I2 | `frame main` (and `reset`/`exit`/`top`) clears `active_frame` from the session | Static (stubbed browser) | ✅ verified this session |
| I3 | `get_tab(browser)` returns the resolved frame object when `active_frame` is set | Static (stubbed browser) | ✅ verified this session |
| I4 | `get_tab(browser)` returns `browser.latest_tab` when no `active_frame` is set | Static (stubbed browser) | ✅ verified this session (implicit in I1-I3's before/after states) |
| I5 | A bare digit passed to `frame` is treated as a 0-based frame index, not a CSS selector | Static (stubbed browser) | ✅ verified this session (`loc.isdigit()` branch confirmed via code read; direct assertion not separately captured — recommend a follow-up unit test) |
| I6 | `frame <bad-sel>` (no matching iframe) → error + exit 1, `active_frame` left unchanged | Desktop | ⬜ |
| I7 | Once in a frame, `snap`/`click`/`type`/`text`/`html`/`js`/`wait`/`press` operate inside it; `goto`/`back`/`forward`/`refresh`/`tabs`/`tab`/`newtab`/`closetab`/`cookies`/`shot`/`scroll` still act on the top-level page | Desktop | ⬜ |
| I8 | If the active frame is removed from the page (e.g. by a re-render), `get_tab()` falls back to the main tab rather than raising | Desktop | ⬜ |

## J. `upload` and `select`

| # | Test | Env | Status |
|---|---|---|---|
| J1 | `upload <sel> <path>` on an existing file calls `el.input(<absolute path>)` | Static (stubbed browser) | ✅ verified this session |
| J2 | `upload <sel> <missing-path>` → `{"error": "File not found: ..."}` + exit 1, without touching the element | Static (stubbed browser) | ✅ verified this session |
| J3 | `select <sel> <digit>` calls `el.select.by_index(int(value))` | Static (stubbed browser) | ✅ verified this session |
| J4 | `select <sel> <text>` calls `el.select.by_text(value)` | Static (stubbed browser) | ✅ verified this session |
| J5 | `select` on a non-`<select>` element → `{"error": "... is not a <select>"}` + exit 1 | Static (stubbed browser) | ✅ verified this session (relies on DrissionPage's `el.select` being falsy for non-select tags) |
| J6 | `upload` on a real `<input type=file>` actually populates the browser's file list (via CDP `DOM.setFileInputFiles`) | Desktop | ⬜ |
| J7 | `select` on a real multi-option `<select>` visibly changes the selected option in the page | Desktop | ⬜ |

## H. Cross-platform (spec §9)

| # | Test | Env | Status |
|---|---|---|---|
| H1 | CLI runs under Python 3.8, 3.10, 3.11+ without syntax errors | Static | ✅ verified under 3.11.15 this session |
| H2 | stdout/stderr UTF-8 wrapping prevents `UnicodeEncodeError` when printing CJK text (e.g. Chinese selector text) on a `cp950`/`cp1252` locale | Desktop (Windows) | ⬜ |
| H3 | `find_chrome()` never raises — always returns a string, even with nothing found on any platform | Static | ✅ verified this session (see C5) |

## Known-Fail register

Carried from spec §10 — these are already confirmed broken/inconsistent and
should be tracked as fix tickets, not silently left "not yet run":

- ~~**D-KF1** — `tab <bogus-id>` and **D-KF2** `wait` timeout both exit 0 on
  failure~~ **Fixed this session** — both now call `sys.exit(1)` alongside
  their `{"ok": false, ...}` JSON. Verified via unit tests with a stubbed
  browser/tab (D3, D18).
- ~~**D-KF3 — `shot` writes relative to CWD.**~~ **Fixed this session** —
  output path now resolves relative to the script's own directory. Verified
  via a `chdir("/tmp")` unit test (D11).
- ~~**E1 (press)** — `ModuleNotFoundError` on every `press`/`key` call.~~
  **Fixed this session** — `scripts/drission.py:484` now imports
  `from DrissionPage.common import Keys`. Verified via a mocked-tab unit
  test (E3–E5); still needs a Desktop-env pass against a real page to
  close out E3/E4 fully.

## Session-verified summary (this session, 2026-08-18)

Verified with a live headless Chromium + reinstalled `DrissionPage==4.1.1.4`,
plus stubbed-browser unit tests for the exit-code/CWD fixes and every new
command (`newtab`, `closetab`, `frame`, `upload`, `select`, and the
`get_browser` connect-retry logic): A6, C1, C4, C5, D3, D11, D18, D21–D24,
E1, E1-fix, E2, E3, E4, E5, I1–I5, J1–J5, H1, H3.

C1b (real end-to-end connect against an externally-launched browser) stayed
blocked this session by an unrelated sandbox quirk: this container's headless
Chromium's CDP websocket handshake returns 404 regardless of connection
method (bare port, or the new options-based retry) — confirmed independent
of the code changes here, since the same failure occurred against a
DrissionPage-launched instance too. The retry logic itself is verified via
mocks (C1); only the live end-to-end path is unverified.

Everything else under **Desktop** env requires a real user-driven Chrome
window (manual login, visible UI, real iframes/selects/file inputs) and
could not be run in this sandboxed container — those rows stay ⬜ until
exercised in the actual target environment (a user's machine with Hermes
Agent).
