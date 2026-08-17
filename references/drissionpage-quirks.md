# DrissionPage 4.x API Gotchas

Detailed reference for debugging selector/API issues with `scripts/drission.py`.
Load this file when a command fails in a way the top-level troubleshooting
table in SKILL.md / README.md doesn't cover.

## Connecting to an existing browser

- `Chromium(port)` expects the target browser to already be reachable on that
  CDP port. If DrissionPage can't resolve a local browser executable path
  (e.g. `set_browser_path` was never called and no `chrome`/`google-chrome`/
  `msedge` binary is on `PATH`), it may raise `FileNotFoundError: The browser
  executable file path cannot be found` even though the CDP endpoint itself
  (`http://localhost:9222/json/version`) responds fine to `curl`. Run
  `python drission.py launch` first, or make sure a Chrome/Edge binary is
  discoverable, before calling `connect`.
- Chrome only allows **one** remote-debugging instance per user-data-dir.
  Close all existing Chrome windows before launching with
  `--remote-debugging-port=9222`, otherwise the new instance silently reuses
  the old profile without opening the debug port.

## Selector formats

- `tab.eles()` / `tab.ele()` use a single `css:` prefix at the start of the
  whole selector string: `"css:a, button, input"` works.
  `"css:a, css:button, css:input"` returns 0 results — don't repeat the
  prefix per clause.
- Bare strings without a prefix do **text matching**, not CSS matching.
  `"#id"` works because it still parses as CSS, but relying on bare strings
  for anything more complex will silently do the wrong kind of match. Prefer
  explicit `css:` or `xpath:` prefixes.
- `text:` selectors can match an inner `<span>` instead of the outer
  clickable `<button>`. For clickable elements prefer CSS
  (`button[type='submit']`) or XPath with `contains(text(), ...)`.
- CSS attribute selectors with special characters (e.g.
  `a[href*='AccountChooser']`) sometimes fail to parse — fall back to a
  simpler selector or XPath.

## JavaScript execution (`js` command / `run_js`)

- `cmd_js` only auto-prepends `return` for a **single expression**. Anything
  containing `;` or a newline is treated as a multi-statement block and is
  wrapped as `function(){ <code> }` — no implicit return. If you need a
  value back, add an explicit `return` statement at the end of the block.
- `from DrissionPage.keys import Keys` does not exist in 4.x. Use
  `from DrissionPage.common import Keys`, or drive key presses via
  `tab.actions.type(Keys.ENTER)`.

## Clicking

- If a click fails with `NoRectError`, the element has no screen position
  (it's hidden or off-screen). The CLI already falls back to
  `click(by_js=True)` automatically; if that still fails, run
  `js "document.querySelector('...').click()"` directly.

## Snapshot refs (`[eN]`)

- `[eN]` refs are cached XPath lookups tied to the page URL at the time
  `snap` ran. They go stale after navigation, form submission, or any DOM
  change — always re-run `snap` before reusing a ref.
- Piping `snap` output through `head`/`grep` in the same terminal call
  doesn't affect the session file — the ref map is written to disk as part
  of `snap` itself, independent of what you do with stdout.

## Amazon scraper (`amazon.py`)

- A "無法配送" (cannot ship) buybox means Amazon is showing a different
  item's price — extract the real price from the page-source variant JSON
  instead of trusting the buybox text.
- On variant-heavy pages, `.a-price` blocks may all be `visible=False`.
  Check visibility before trusting a scraped price.
- Some prices render as bare text outside `.a-offscreen` — regex-fallback
  against the buybox text in that case.
