import base64
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright

import storage

mcp = FastMCP("ui-spatial-memory")

JS_EXTRACT_ELEMENTS = """
() => {
    const selectors = 'button, a, input, select, textarea, [role="button"], [role="link"], [role="tab"], [role="menuitem"], [onclick], [contenteditable]';
    const els = document.querySelectorAll(selectors);
    const seen = new Set();
    const results = [];

    for (const el of els) {
        if (seen.has(el)) continue;
        seen.add(el);

        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) continue;

        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;

        // Build a unique CSS selector
        let selector = el.tagName.toLowerCase();
        if (el.id) {
            selector = '#' + el.id;
        } else if (el.className && typeof el.className === 'string') {
            selector += '.' + el.className.trim().split(/\\s+/).join('.');
        }

        const text = (el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || '').trim().substring(0, 100);

        results.push({
            tag: el.tagName.toLowerCase(),
            text: text,
            role: el.getAttribute('role') || '',
            selector: selector,
            bbox: {
                x: Math.round(rect.x),
                y: Math.round(rect.y),
                width: Math.round(rect.width),
                height: Math.round(rect.height)
            },
            center: {
                x: Math.round(rect.x + rect.width / 2),
                y: Math.round(rect.y + rect.height / 2)
            },
            interactable: true
        });
    }
    return results;
}
"""


@mcp.tool()
async def capture_map(url: str, viewport_width: int = 1280, viewport_height: int = 720) -> dict:
    """Capture a page layout as a structured spatial map of all interactable elements."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": viewport_width, "height": viewport_height})
            await page.goto(url, wait_until="networkidle", timeout=30000)

            screenshot_bytes = await page.screenshot()
            phash = storage.compute_phash(screenshot_bytes)

            elements = await page.evaluate(JS_EXTRACT_ELEMENTS)

            await browser.close()

        map_id = hashlib.sha256(f"{url}|{viewport_width}x{viewport_height}".encode()).hexdigest()[:16]

        map_data = {
            "map_id": map_id,
            "source": url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phash": phash,
            "viewport": {"width": viewport_width, "height": viewport_height},
            "elements": elements,
        }

        storage.save_map(map_data)
        return map_data

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def lookup_element(map_id: str, query: str) -> dict:
    """Look up elements in a stored map by text, tag, role, or selector. Returns matching elements with click coordinates."""
    map_data = storage.load_map(map_id)
    if map_data is None:
        return {"error": f"Map '{map_id}' not found"}

    q = query.lower()
    exact = []
    partial = []

    for el in map_data.get("elements", []):
        text = (el.get("text") or "").lower()
        tag = (el.get("tag") or "").lower()
        role = (el.get("role") or "").lower()
        selector = (el.get("selector") or "").lower()

        if q == text:
            exact.append(el)
        elif q in text or q in tag or q in role or q in selector:
            partial.append(el)

    matches = exact + partial
    return {
        "map_id": map_id,
        "query": query,
        "match_count": len(matches),
        "elements": matches,
    }


@mcp.tool()
async def match_screen(screenshot_base64: str) -> dict:
    """Match a screenshot against stored maps using perceptual hashing to find a previously captured layout."""
    try:
        screenshot_bytes = base64.b64decode(screenshot_base64)
        phash = storage.compute_phash(screenshot_bytes)
        result = storage.find_matching_map(phash)

        if result:
            distance = result.pop("_distance")
            return {
                "matched": True,
                "map_id": result["map_id"],
                "source": result["source"],
                "element_count": len(result.get("elements", [])),
                "distance": distance,
            }
        return {"matched": False, "suggestion": "Use capture_map to create a new map"}

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
