# Nova

Hands-free PC voice assistant (Windows).

## Current Phase

**Phase 6 — Browser Control (Playwright)**

```
👂 "Hey Nova"
      ↓
🎤 Listening
      ↓
📝 STT (faster-whisper)
      ↓
🧠 Fast router → LLM (validated JSON only)
      ↓
🌐 BrowserController (Playwright, reused session)
      ↓
🔊 Response
```

One browser action per utterance, no multi-step, no vision, no credentials.

---

## Features

### Phase 1-2: STT + TTS
- Mic detection, 16kHz, `faster-whisper`; `pyttsx3`

### Phase 3: Wake Word
- `vosk` `hey nova`, state machine, `--manual`

### Phase 4: PC Control
- Apps/websites, type, keys, hotkeys, mouse via allowlists

### Phase 5: Natural Language
- LLM `CommandInterpreter` (openai), `validate_action` strict, `SYSTEM_PROMPT` JSON only, fast path bypasses LLM

### Phase 6 — Browser Control (new)
- **Playwright** reused `BrowserController` (`chromium`/`firefox`/`webkit`, `headless=false` so user sees browser)
- **Sites:** `app/browser/sites.py` `WEBSITE_ALIASES` + `google_search_url` / `youtube_search_url`
- **Open website:** `open_url` alias or URL → `page.goto`
- **Search web:** `search_web` → `https://www.google.com/search?q=...` URL encoded
- **YouTube search:** `youtube_search` → robust selectors `input#search`, `ytd-searchbox` etc. → fill + Enter, fallback to URL
- **Navigation:** `browser_back` / `browser_forward` / `browser_refresh` via `page.go_back/forward/reload`
- **Scroll:** `browser_scroll` via `page.mouse.wheel` (no `pyautogui` coordinates)
- **Close:** `close_browser` only Nova's session, not all browsers
- **State:** `running`, `current_url`, `title` in memory, reused session not per-command launch
- **Validation:** extended `schemas.py` `search_web/youtube_search/browser_* /close_browser`, `prompts.py` browser examples, never `page.click(...code)`
- **Privacy/Security:** no screenshots, cookies, history, passwords, no page content to LLM, only `query` needed

---

## Requirements

- Python 3.11+, Windows 10/11, mic + speakers

---

## Installation

```powershell
cd nova
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
```

Vosk model auto-downloads to `models/vosk-model-small-en-us-0.15`.

LLM (optional):
```powershell
copy .env.example .env
# LLM_ENABLED=true LLM_API_KEY=sk-...
```

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `base` |  |
| `BROWSER_ENABLED` | `true` |  |
| `BROWSER_NAME` | `chromium` | `chromium/firefox/webkit` |
| `BROWSER_HEADLESS` | `false` | `false` = visible |
| `BROWSER_TIMEOUT_MS` | `10000` | 1k–60k |
| `LLM_ENABLED` | `false` |  |
| `PC_CONTROL_ENABLED` | `true` |  |

---

## Usage

Hands-free:
```powershell
python -m app.main
# 👂 Waiting for "hey nova"...
# Hey Nova → "open YouTube" → YouTube loads
# Hey Nova → "search YouTube for Arijit Singh" → YouTube search results
# Hey Nova → "search Google for Python tutorials" → Google results
# Hey Nova → "go back" → browser back
# Hey Nova → "scroll down" → Playwright scroll
# Hey Nova → "close the browser" → Nova's browser closes
```

Manual:
```powershell
python -m app.main --manual
```

Supported browser natural variations (fast without LLM for exact, LLM for natural):
```
"Open YouTube" / "Go to YouTube" / "Take me to YouTube"
"Search YouTube for Arijit Singh" / "Find Arijit Singh on YouTube" / "Look up Arijit Singh on YouTube"
"Search Google for Python tutorials" / "Google Python tutorials" / "Look up Python tutorials"
"Go back" / "Go forward" / "Refresh" / "Scroll down" / "Close the browser"
```
Per spec one action per utterance; `open Brave, go to YouTube…` → `I can handle one basic action…`

---

## Project Structure

```
nova/
├── app/
│   ├── main.py                 # PC+Browser+LLM routing, lifecycle
│   ├── config.py               # +BROWSER .env
│   ├── speech/transcriber.py
│   ├── tts/speaker.py
│   ├── wakeword/detector.py
│   ├── pc/{controller,actions}
│   ├── ai/{interpreter,schemas,prompts}
│   └── browser/                # NEW Phase 6
│       ├── __init__.py
│       ├── controller.py       # BrowserController Playwright
│       ├── actions.py          # handle_browser_command fast router
│       └── sites.py            # WEBSITE_ALIASES + URL helpers
├── .env.example
├── requirements.txt            # +playwright
└── README.md
```

---

## Privacy / Safety

- Wake/STT/TTS/PC local; browser Playwright local, no screenshots/cookies/history to LLM, only `query`/`website` needed; no password/CAPTCHA/purchase; no `pyautogui.click(x,y)` for browser; single action per command.

---

## Roadmap

- [x] Phase 1 STT
- [x] Phase 2 TTS
- [x] Phase 3 Wake Word
- [x] Phase 4 PC Control
- [x] Phase 5 Natural Language
- [x] Phase 6 Browser Control (current)
- [ ] Phase 7+ vision, multi-step

## License

MIT
