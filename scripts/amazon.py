#!/usr/bin/env python3
"""
Amazon price scraper — DrissionPage browser skill helper.
Searches Amazon and extracts product prices, drilled into detail pages.

Usage:
  python amazon.py search "ryzen ai max+ 395 128gb"    # search and list
  python amazon.py search "max 395" --min-ram 128       # filter by RAM
  python amazon.py search "max 395" --detail            # also visit each detail page
  python amazon.py detail <asin>                         # drill into one product
"""

import json
import sys
import time
from pathlib import Path

# Force UTF-8 output — prevents UnicodeEncodeError on Windows CP950/CP1252
import io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

HERMES_HOME = Path(__file__).resolve().parents[4]  # ~/.hermes/
SESSION_FILE = HERMES_HOME / "drission_session.json"

# ── helpers ──────────────────────────────────────────────────────────

def load_session():
    if SESSION_FILE.exists():
        return json.loads(SESSION_FILE.read_text())
    return {}

def get_browser():
    from DrissionPage import Chromium
    session = load_session()
    port = session.get("debug_port", 9222)
    return Chromium(port)

def extract_results(tab):
    """Extract search result cards from Amazon page."""
    items = []
    # Try multiple selector patterns (Amazon changes these)
    cards = tab.eles("css:[data-component-type='s-search-result']", timeout=3)
    if not cards:
        cards = tab.eles("css:.s-result-item[data-asin]", timeout=3)

    for card in cards:
        try:
            asin = card.attr("data-asin")
            if not asin or asin == "null":
                continue

            title_el = card.ele("css:h2 span", timeout=0.5) or card.ele("css:h2", timeout=0.5)
            title = title_el.text.strip() if title_el else "N/A"
            if not title or len(title) < 10:
                continue

            # Price
            price_whole = card.ele("css:.a-price-whole", timeout=0.3)
            price_frac = card.ele("css:.a-price-fraction", timeout=0.3)
            price_sym = card.ele("css:.a-price-symbol", timeout=0.3)
            price = "N/A"
            if price_whole:
                sym = price_sym.text.strip() if price_sym else "$"
                p = price_whole.text.replace("\n", "").strip()
                if price_frac:
                    p += "." + price_frac.text.strip()
                price = f"{sym}{p}"

            # Rating
            rating_el = card.ele("css:.a-icon-star-small .a-icon-alt", timeout=0.2)
            rating = rating_el.text.strip() if rating_el else "N/A"

            # RAM detection from title
            import re
            ram_match = re.search(r"(\d+)\s*GB\s*(RAM|LPDDR)", title, re.IGNORECASE)
            ram = f"{ram_match.group(1)}GB" if ram_match else "?"

            # Storage detection
            ssd_match = re.search(r"(\d+)\s*TB\s*(SSD|PCIe|NVMe)", title, re.IGNORECASE)
            storage = f"{ssd_match.group(1)}TB" if ssd_match else "?"

            items.append({
                "asin": asin,
                "title": title[:150],
                "price": price,
                "rating": rating,
                "ram": ram,
                "storage": storage,
                "link": f"https://www.amazon.com/dp/{asin}",
            })
        except Exception:
            continue

    return items


def extract_detail(tab):
    """Extract price and specs from a product detail page.
    
    Handles Amazon edge cases:
    - "Cannot ship to your location" → extracts price from variant JSON instead
    - Multiple hidden .a-price blocks → only uses VISIBLE prices
    - Dynamic variant prices → falls back to page source JSON parsing
    """
    import re, json as json_mod
    
    info = {"title": tab.title, "url": tab.url}

    # ── Step 1: Check if buybox is blocked (cannot ship) ──
    buybox = None
    for sel in ["#desktop_buybox", "#buybox", "#buybox_feature_div"]:
        buybox = tab.ele(f"css:{sel}", timeout=1)
        if buybox:
            break
    
    cannot_ship = False
    if buybox:
        buybox_text = buybox.text.strip()
        cannot_ship = any(phrase in buybox_text for phrase in [
            "無法配送", "cannot be shipped", "does not ship", 
            "cannot ship", "無法運送", "doesn't ship"
        ])
        if cannot_ship:
            info["cannot_ship"] = True
            info["buybox_message"] = buybox_text[:200]

    # ── Step 2a: If cannot ship, extract price from page source JSON ──
    if cannot_ship:
        html = tab.html
        # Look for the variant JSON with price data
        price_matches = re.findall(
            r'"priceWithoutCurrencySymbol":"([\d.]+)".*?"olpMessage":"([^"]*)"',
            html
        )
        if price_matches:
            for price_str, message in price_matches:
                if "US$" in message or "$" in message:
                    info["price_on_page"] = f"US${price_str}"
                    info["price_source"] = "variant_JSON"
                    break
        
        if not info.get("price_on_page"):
            # Fallback: search for any price near "128GB" in JSON
            ram_price = re.findall(
                r'"128GB[^"]*".*?"priceWithoutCurrencySymbol":"([\d.]+)"',
                html
            )
            if ram_price:
                info["price_on_page"] = f"US${ram_price[0]}"
                info["price_source"] = "RAM_filtered_JSON"

    # ── Step 2b: Normal case — use visible price elements ──
    if not info.get("price_on_page"):
        for sel in [
            "css:.a-price .a-offscreen",
            "css:#corePriceDisplay_desktop_feature_div .a-offscreen",
            "css:.apexPriceToPay .a-offscreen",
            "css:#price_inside_buybox",
        ]:
            els = tab.eles(sel, timeout=1)
            for el in els:
                try:
                    if el.states.is_displayed:
                        info["price_on_page"] = el.text.strip()
                        info["price_source"] = f"visible_{sel}"
                        break
                except:
                    pass
            if info.get("price_on_page"):
                break

    # ── Step 2c: Fallback — parse buybox text for price ──
    if not info.get("price_on_page") and buybox:
        match = re.search(r'US?\$[\d,]+\.\d{2}', buybox_text)
        if match:
            info["price_on_page"] = match.group()
            info["price_source"] = "buybox_text_regex"
        else:
            # Try total price line
            match = re.search(r'總計\s+US?\$([\d,]+\.\d{2})', buybox_text)
            if match:
                info["price_on_page"] = f"US${match.group(1)}"
                info["price_source"] = "buybox_total"
            else:
                match = re.search(r'Total\s+US?\$([\d,]+\.\d{2})', buybox_text)
                if match:
                    info["price_on_page"] = f"US${match.group(1)}"
                    info["price_source"] = "buybox_total_en"

    # ── Step 3: Extract all visible dollar amounts as reference ──
    try:
        body_text = tab.ele("css:body", timeout=1)
        if body_text:
            all_prices = re.findall(r'\$[\d,]+\.\d{2}', body_text.text)
            info["all_visible_prices"] = list(set(all_prices))[:20]
    except:
        pass

    # ── Step 4: Specs table ──
    try:
        rows = tab.eles("css:#productDetails_techSpec_section_1 tr, css:#productDetails_detailBullets_sections1 tr", timeout=1)
        specs = {}
        for row in rows:
            th = row.ele("css:th", timeout=0.2)
            td = row.ele("css:td", timeout=0.2)
            if th and td:
                specs[th.text.strip()] = td.text.strip()[:200]
        info["specs"] = specs
    except Exception:
        pass

    return info


# ── commands ─────────────────────────────────────────────────────────

def cmd_search(query, min_ram=None, detail=False):
    browser = get_browser()
    tab = browser.latest_tab

    # Navigate to search
    import urllib.parse
    url = f"https://www.amazon.com/s?k={urllib.parse.quote(query)}"
    tab.get(url)
    time.sleep(2)

    items = extract_results(tab)

    # Filter by RAM
    if min_ram:
        items = [i for i in items if i["ram"] != "?" and int(i["ram"].replace("GB", "")) >= min_ram]

    print(f"\n=== Amazon Search: \"{query}\" ===")
    print(f"Found {len(items)} results\n")

    for i, item in enumerate(items):
        ram_tag = f"[{item['ram']}]" if item["ram"] != "?" else ""
        storage_tag = f"[{item['storage']}]" if item["storage"] != "?" and item["storage"] != "?TB" else ""
        print(f"{i+1}. {item['title'][:100]}")
        print(f"   Price: {item['price']}  {ram_tag} {storage_tag}  ★ {item['rating']}")
        print(f"   Link: {item['link']}")
        print()

        # Drill into detail page
        if detail and item["asin"]:
            print(f"   --- Detail page ---")
            tab.get(item["link"])
            time.sleep(2)
            d = extract_detail(tab)
            print(f"   Title: {d['title'][:120]}")
            print(f"   Price on page: {d.get('price_on_page', 'N/A')}")
            if d.get("specs"):
                print(f"   Key specs:")
                for k, v in list(d["specs"].items())[:8]:
                    print(f"     {k}: {v}")
            print()
            tab.back()
            time.sleep(1)

    # JSON summary for agent consumption
    print("---JSON---")
    print(json.dumps(items, ensure_ascii=False, indent=2))


def cmd_detail(asin):
    browser = get_browser()
    tab = browser.latest_tab
    tab.get(f"https://www.amazon.com/dp/{asin}")
    time.sleep(2)
    d = extract_detail(tab)

    print(f"Title: {d['title']}")
    print(f"URL: {d['url']}")
    print(f"Price: {d.get('price_on_page', 'N/A')}")
    if d.get("specs"):
        print(f"\nSpecs:")
        for k, v in d["specs"].items():
            print(f"  {k}: {v}")


# ── main ─────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python amazon.py search <query> [--min-ram N] [--detail]")
        print("       python amazon.py detail <asin>")
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "search":
        query_parts = []
        detail = False
        min_ram = None
        for a in args:
            if a == "--detail":
                detail = True
            elif a == "--min-ram":
                idx = args.index(a)
                if idx + 1 < len(args):
                    min_ram = int(args[idx + 1])
            elif a.startswith("--min-ram="):
                min_ram = int(a.split("=")[1])
            elif not a.startswith("--"):
                query_parts.append(a)
        query = " ".join(query_parts)
        if not query:
            print("Error: search query required")
            sys.exit(1)
        cmd_search(query, min_ram=min_ram, detail=detail)

    elif cmd == "detail":
        if not args:
            print("Error: ASIN required")
            sys.exit(1)
        cmd_detail(args[0])

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
