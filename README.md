# Nova

Hands-free PC voice assistant (Windows).

## Current Phase

**Phase 7 — Screen Understanding + Visual Control Foundation**

```
👂 "Hey Nova"
      ↓
🎤 Listening (no ENTER)
      ↓
📝 STT (faster-whisper)
      ↓
🧠 Fast router (vision → browser → pc) → LLM (validated JSON)
      ↓
👁️ Vision (MSS on-demand screenshot only on visual commands)
   🌐 Browser (Playwright reused) / 🖥️ PC (allowlisted)
      ↓
🔊 Response
```

Foundation for seeing the screen, not yet autonomous clicking. No multi-step agent, no password handling.

---

## Features

### Phase 1-2: STT + TTS
- `faster-whisper` 16kHz, `pyttsx3` SAPI5

### Phase 3: Wake Word
- `vosk` `hey nova`, state machine, `winsound` beep, `--manual`

### Phase 4: PC Control
- Apps/websites, type, keys, hotkeys allowlisted, mouse, `win32gui` foreground window

### Phase 5: Natural Language
- `CommandInterpreter` (openai), `validate_action`, fast local bypasses LLM

### Phase 6: Browser
- Playwright `BrowserController` reused, `open_url/search_web/youtube_search/back/forward/refresh/scroll/close`, `sites.py` aliases

### Phase 7 — Vision (new)
- **`app/vision/screenshot.py` `ScreenCapture`**: MSS primary (fallback PIL ImageGrab), `list_monitors()` (primary/all/1/2), `capture_screen()`→PIL in memory (not saved), resize to `SCREENSHOT_MAX_WIDTH/HEIGHT` preserving aspect, `vision_to_screen()` coordinate conversion with monitor offset/scale, `capture_and_encode()` base64 PNG for vision API, on-demand only.
- **`app/vision/schemas.py`**: `ScreenElement` (type `button/text/input/link/image/icon/menu/window/unknown`, `label,x,y,width,height,confidence`, `center()`, `is_valid()`), `ScreenAnalysis` (description, elements, active_window, monitor, confidence), `FindResult` (found,x,y,width,height,confidence), `validate_element()` with `VISION_MIN_CONFIDENCE` (default 0.70).
- **`app/vision/analyzer.py` `ScreenAnalyzer`**: provider abstraction (openai vision `gpt-4o-mini`/`gpt-4o`), `analyze(question, active_window)` and `find_element(target, active_window)` — captures via `ScreenCapture`, sends base64 + question to vision API only when visual command triggered, handles timeout `VISION_TIMEOUT_SECONDS` (15), fallback local description (`active_window is open. Screen ...`) when no API key, confidence filtering, `safe_click(element)` only if `VISION_CLICK_TEST_ENABLED=true` and confidence≥threshold (default disabled).
- **Active window:** `PCController.get_foreground_window()` via `win32gui` (title, position, size) used as hint for vision.
- **Routing:** `app/main.py` `route_pc_command` vision fast local `_handle_vision_local` before browser/pc — triggers on `"what is on my screen" / "what do you see" / "what app is open" / "where is the …" / "find the …"`; normal `open Brave` does NOT capture; LLM validated vision actions `analyze_screen`/`find_screen_element`/`get_active_window` dispatched to `ScreenAnalyzer` with on-demand screenshot, timeout `Screen analysis timed out.` not crash.
- **Privacy:** screenshots in RAM only, not logged/saved/uploaded unless explicit visual command, not sent while idle, not sent to text LLM, only to vision provider for that request; `VISION_MIN_CONFIDENCE` rejects low results; `VISION_CLICK_TEST_ENABLED=false` default prevents arbitrary clicking.

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

Configure:
```powershell
copy .env.example .env
notepad .env
# LLM: LLM_ENABLED=true LLM_API_KEY=sk-... (for natural + vision)
# Vision: VISION_ENABLED=true VISION_PROVIDER=openai VISION_MODEL=gpt-4o-mini VISION_API_KEY=sk-... (fallback to LLM key) VISION_TIMEOUT_SECONDS=15 SCREEN_MONITOR=primary SCREENSHOT_MAX_WIDTH=1600 VISION_MIN_CONFIDENCE=0.70 VISION_CLICK_TEST_ENABLED=false
```

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `VISION_ENABLED` | `true` | Enable vision |
| `VISION_PROVIDER` | `""` (→llm_provider) | `openai` |
| `VISION_MODEL` | `gpt-4o-mini` | vision model |
| `VISION_API_KEY` | _(llm key fallback)_ | vision API key |
| `VISION_TIMEOUT_SECONDS` | `15` | 1–60 |
| `SCREEN_MONITOR` | `primary` | `primary/all/1/2` |
| `SCREENSHOT_MAX_WIDTH` | `1600` | 320–3840 |
| `SCREENSHOT_MAX_HEIGHT` | `1000` | 240–2160 |
| `VISION_MIN_CONFIDENCE` | `0.70` | 0–1 |
| `VISION_CLICK_TEST_ENABLED` | `false` | safe click gate |

Plus Phase 1-6 vars (WHISPER, TTS, WAKE, PC, BROWSER, LLM).

---

## Usage

Hands-free:
```powershell
python -m app.main
# 👂 Waiting for "hey nova"...
# Hey Nova → "what is on my screen?" → captures → "Google Chrome is open. YouTube is visible."
# Hey Nova → "where is the YouTube search box?" → "I found YouTube search box near 740, 120."
# Hey Nova → "what application is open?" → "Visual Studio Code is open."
# Hey Nova → "open YouTube" → (no screenshot)
```

Manual:
```powershell
python -m app.main --manual
```

Visual natural variations via LLM:
```
"What is on my screen?" → analyze_screen
"What do you see?" → analyze_screen
"Find the YouTube search box." → find_screen_element
"Where is the Play button?" → find_screen_element
"Is there a browser open?" → get_active_window
```

One visual action per utterance; low confidence → "I'm not confident enough…"; not found → "I couldn't find that…"; timeout → "Screen analysis timed out."

---

## Project Structure

```
nova/
├── app/
│   ├── main.py                 # vision/browser/pc + LLM routing, on-demand capture
│   ├── config.py               # +VISION
│   ├── speech/transcriber.py
│   ├── tts/speaker.py
│   ├── wakeword/detector.py
│   ├── pc/{controller,actions}
│   ├── ai/{interpreter,schemas,prompts}  # +vision actions
│   ├── browser/{controller,actions,sites}
│   └── vision/                 # NEW Phase 7
│       ├── __init__.py
│       ├── screenshot.py       # ScreenCapture MSS
│       ├── analyzer.py         # ScreenAnalyzer vision
│       └── schemas.py          # ScreenElement etc.
├── .env.example
├── requirements.txt            # +mss, Pillow
└── README.md
```

---

## Privacy / Safety

- Screenshots on-demand only for `analyze_screen`/`find_screen_element`, not for `open Brave` etc.; in RAM, base64 not logged, not saved, not sent while idle, only to vision provider for that request, not to text LLM; `VISION_MIN_CONFIDENCE` gate, `VISION_CLICK_TEST_ENABLED=false` blocks auto click; never continuous upload, no passwords.

---

## Roadmap

- [x] Phase 1 STT
- [x] Phase 2 TTS
- [x] Phase 3 Wake Word
- [x] Phase 4 PC Control
- [x] Phase 5 Natural Language
- [x] Phase 6 Browser Control
- [x] Phase 7 Screen Understanding (current)
- [ ] Phase 8 multi-step visual agent

## License

MIT
