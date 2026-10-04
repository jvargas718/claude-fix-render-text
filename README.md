# fix-render-text

A Claude Code skill that fixes the garbled, made-up text AI image generators put on packaging and product renders. Claude checks the render against your tech pack, shows you what's wrong, then drives Photoshop to remove the bad text and set the correct copy as **live text you can still change**, matched to the angle and focus of the surface.

## Quick start (no coding needed)

1. **Install the skill:** download **[fix-render-text.zip](https://github.com/jvargas718/claude-fix-render-text/releases/latest/download/fix-render-text.zip)**, unzip it, and move the `fix-render-text` folder into `~/.claude/skills/`. Create that folder if it doesn't exist. No renaming needed.
2. **Open Claude Code** (the desktop app's Code tab works) and say:
   > *"Set up the fix-render-text skill. Install what it needs."*

   Claude reads the setup section below and walks you through it, asking before it installs anything. It takes about 15 minutes the first time.
3. **Use it:** open your render in Photoshop and your tech pack in Illustrator, then say:
   > *"Fix the text in this render. Check it against the tech pack."*

## Three ways to use it

| Mode | When | What happens |
|---|---|---|
| **With a tech pack** | You have the approved copy (Illustrator `.ai` with live or outlined text, a PDF, or a copy doc) | Claude compares every line of the render against it, shows you a table of fixes to approve, then fixes the render in Photoshop. |
| **No tech pack** | There's nothing to check against | Claude keeps what's already right, **flags every fact** (temperatures, times, amounts, claims, legal marks) and asks you in **one numbered sheet** instead of guessing. It can suggest wording, but never invents numbers. In production mode, every line in the change log gets a source. |
| **Batch** (colorways, re-exports) | A range of renders of the same product | Fix and approve the first one. Claude carries the fix to the rest, **aligning automatically** even if a render was cropped, scaled or rotated differently, and re-samples each colorway's print color. You get a layered PSD and a change log per render, plus one before/after sheet. |

Batch mode also uses OpenCV for alignment. `uv` installs it on the fly, so there's nothing extra to set up.

## What you need

| What | Why | Cost |
|---|---|---|
| A Mac | Uses macOS's built-in text recognition | n/a |
| Adobe Photoshop (2024 or newer) | Where the fixing happens | Your Adobe plan |
| Adobe Illustrator (optional) | Only to read `.ai` tech packs. PDFs or typed copy also work | Your Adobe plan |
| Claude Code | Runs the skill | Your Claude plan |
| **Photoshop MCP server** ([alisaitteke/photoshop-mcp](https://github.com/alisaitteke/photoshop-mcp)) | Lets Claude control Photoshop | Free, open source (MIT) |
| **Illustrator MCP server** ([krVatsal/illustrator-mcp](https://github.com/krVatsal/illustrator-mcp)), optional | Lets Claude read tech packs in Illustrator | Free, open source (MIT) |
| `uv`, Node.js, Xcode command-line tools | Run the two servers and the skill's scripts | Free |

The fix itself uses no Adobe generative credits. The skill only uses generative fill if you approve it.

## Setup (Claude follows this, or do it yourself)

**Tools:**
```bash
xcode-select --install                                   # swift, for text recognition
curl -LsSf https://astral.sh/uv/install.sh | sh          # uv, for Python
```
Node.js 18+: install from [nodejs.org](https://nodejs.org) if `node --version` doesn't work.

**Photoshop server.** Reviewed at commit `ecd502c` (v1.7.32). Build from that exact commit so new code can't arrive without you checking it:
```bash
git clone https://github.com/alisaitteke/photoshop-mcp ~/photoshop-mcp
cd ~/photoshop-mcp && git checkout ecd502c
npm ci --ignore-scripts && npm rebuild better-sqlite3 && npm run build:server
```
It sends anonymous usage analytics by default. Turn them off with `ANALYTICS_DISABLED=1`, as in the config below.

**Illustrator server** (optional). Reviewed at commit `5040dde`:
```bash
git clone https://github.com/krVatsal/illustrator-mcp ~/illustrator-mcp
cd ~/illustrator-mcp && git checkout 5040dde
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python3 -r requirements.txt
```
Its screenshot tool captures your **whole screen**, so close private windows while it's in use.

**Connect them to Claude.** Add these under `mcpServers` in `~/Library/Application Support/Claude/claude_desktop_config.json`, replacing `<home>` with your home folder (for example `/Users/yourname`):
```json
"photoshop": { "command": "node", "args": ["<home>/photoshop-mcp/dist/index.js"], "env": { "ANALYTICS_DISABLED": "1" } },
"illustrator": { "command": "<home>/illustrator-mcp/.venv/bin/python3", "args": ["<home>/illustrator-mcp/illustrator/server.py"] }
```
Fully quit and reopen Claude. Allow macOS's **Automation** prompts, and **Screen Recording** if asked.

**Check it works:** ask Claude *"What version of Photoshop is running?"*

## Good to know
- Your original render is never changed. You get a layered PSD next to it, with the corrected text, a cleanup layer and the untouched original.
- Claude never invents specs, claims or legal marks. Anything it can't verify against your source is flagged for you to decide.
- Tested on macOS with Photoshop 2026 and Illustrator 2026.

## Updates
New versions are published as [releases](https://github.com/jvargas718/claude-fix-render-text/releases). The link above always downloads the latest. To update, replace your `fix-render-text` folder with the new one.

## Support
Shared as is, for free. Issues and suggestions are welcome in the **Issues** tab, and I'll reply when I can. Adobe updates or new versions of the servers can occasionally break a step. If something stops working, an issue with your macOS, Photoshop and Illustrator versions helps a lot.

## Credits and license
This skill is MIT-licensed (see `LICENSE`), by Jose Vargas. Photoshop server by Ali Sait Teke; Illustrator server by Vatsal Kumar. Both are MIT-licensed. Review any newer versions before upgrading.
