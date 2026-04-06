# UI Spatial Memory

**Give AI agents a photographic memory for every UI they visit.**

## The Problem

AI agents treat every screen like they've never seen it before. Each visit means re-parsing the entire UI, burning tokens on element discovery, and guessing at click targets they already found five minutes ago. There's no concept of "I've been here before" -- so agents are slow, expensive, and brittle.

UI Spatial Memory fixes this. It gives agents persistent, coordinate-level recall of every page they've visited via three MCP tools.

## How It Works

1. **Agent visits a page** -- `capture_map` opens the URL in a headless browser, extracts every interactable element with its bounding box and center coordinates, and stores the result as a spatial map.

2. **Agent returns later** -- `match_screen` takes a screenshot and uses perceptual hashing to recognize the page. No URL matching, no DOM diffing -- it works even if the URL has changed.

3. **Agent needs to click something** -- `lookup_element("submit button")` searches the stored map and returns exact `{x, y}` coordinates. No re-parsing required.

## Quick Start

```bash
pip install mcp playwright imagehash Pillow
playwright install chromium
```

### Claude Desktop

Add to your MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "ui-spatial-memory": {
      "command": "python",
      "args": ["/path/to/ui-spatial-memory/server.py"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add ui-spatial-memory python /path/to/server.py
```

## Tools Reference

| Tool | Parameters | Returns |
|------|-----------|---------|
| `capture_map` | `url`, `viewport_width?` (1280), `viewport_height?` (720) | Full spatial map with element coordinates, perceptual hash, map ID |
| `match_screen` | `screenshot_base64` | Match result with `map_id`, source URL, element count, hash distance |
| `lookup_element` | `map_id`, `query` | Matching elements with `center.x`, `center.y` click coordinates |

`lookup_element` searches across element text, tag name, ARIA role, and CSS selector. Exact text matches are ranked first.

## Map Format

Each captured map is stored as JSON in the `maps/` directory:

```json
{
  "map_id": "a1b2c3d4e5f67890",
  "source": "https://example.com/dashboard",
  "timestamp": "2026-04-06T12:00:00+00:00",
  "phash": "d4c3b2a190807060",
  "viewport": { "width": 1280, "height": 720 },
  "elements": [
    {
      "tag": "button",
      "text": "Submit",
      "role": "button",
      "selector": "button.btn-primary",
      "bbox": { "x": 500, "y": 400, "width": 120, "height": 40 },
      "center": { "x": 560, "y": 420 },
      "interactable": true
    }
  ]
}
```

## Roadmap

- Native app support (accessibility tree extraction via platform APIs)
- Vision model fallback for unlabeled elements
- Map diffing (detect UI changes between visits)
- JSON Canvas export for visualizing page maps as spatial graphs in Obsidian
- Element interaction history tracking

## License

MIT
