# Nova

Hands-free PC voice assistant (Windows).

## Current Phase

**Phase 4 — Hands-Free + Basic PC Control**

```
👂 "Hey Nova"  →  🎤 Listening  →  📝 STT (faster-whisper)
      ↓
🧠 Command routing (local, no LLM)
      ↓
🖥️  PC action (app / url / type / key / scroll / click)
      ↓
🔊 Voice response
      ↓
👂 Waiting again
```

Offline, local, allowlisted. No cloud, no LLM, one action per utterance.

---

## Features

### Phase 1 — STT
- Mic detection, 16 kHz mono recording, local `faster-whisper`

### Phase 2 — TTS
- `pyttsx3` SAPI5, configurable voice/rate/volume, `Speaker` reuse

### Phase 3 — Wake Word
- `vosk` small model `hey nova` (dummy fallback), state machine, cooldown/TTS echo prevention, `--manual` fallback

### Phase 4 — PC Control (new)
- **Apps:** `open Notepad / Brave / Chrome / Calculator / VS Code / File Explorer / Edge / Firefox` (aliases, env path overrides `BRAVE_PATH` etc.)
- **Websites:** `open YouTube / GitHub / Google / Gmail` etc. via `webbrowser`
- **Type:** `type Hello World` — literally types, not interpreted
- **Keys:** `press Enter / Escape / Tab / Space / Delete / Up / Down / Home / End / Page Up / Down` (+ F1-F12)
- **Hotkeys:** allowlisted only `Ctrl+C/V/A/Z/S/X/Y/N/O/F/P/W`, `Ctrl+Shift+T/N`, `Alt+Tab/F4`, `Win+D/E/R/L`
- **Mouse:** `click`, `double click`, `right click`, `scroll up/down`
- **Router:** `app/pc/actions.py` normalizes voice, handles variations `open/launch/start/run/go to`, rejects multi-step (`I can handle one...`) and unknown (`I can't perform that action yet.`), never `os.system(user_text)`
- **Safety:** blocklisted `delete/format/kill/password/send email` etc., disabled when `PC_CONTROL_ENABLED=false`, foreground window via `win32gui`

---

## Requirements

- Python 3.11+, Windows 10/11, mic + speakers, internet first run for Whisper

---

## Installation

```powershell
cd nova
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

Vosk model auto-downloads (40MB) or manually extract to `models/vosk-model-small-en-us-0.15`.

---

## Configuration

```powershell
copy .env.example .env
notepad .env
```

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `base` | `tiny`/`base`/`small`/`medium` |
| `WHISPER_DEVICE` | `cpu` | `cpu`/`cuda` |
| `TTS_ENABLED` | `true` | Enable TTS |
| `TTS_RATE` | `175` | 50–400 |
| `TTS_VOLUME` | `1.0` | 0.0–1.0 |
| `WAKE_WORD_ENABLED` | `true` | Hands-free |
| `WAKE_WORD` | `hey nova` | Phrase |
| `WAKE_WORD_THRESHOLD` | `0.5` | Sensitivity |
| `COMMAND_TIMEOUT_SECONDS` | `8` | s after wake |
| `PC_CONTROL_ENABLED` | `true` | Enable PC control |
| `DEFAULT_SCROLL_AMOUNT` | `5` | 1–20 |
| `ACTION_TIMEOUT_SECONDS` | `10` | 1–30 |
| `BRAVE_PATH` | _(PATH)_ | Optional `brave.exe` full path |
| `CHROME_PATH` | _(PATH)_ | Optional `chrome.exe` |
| `VSCODE_PATH` | _(PATH)_ | Optional `Code.exe` |

---

## Usage

Hands-free:
```powershell
python -m app.main
# 👂 Waiting for "hey nova"...
# Say: Hey Nova → 🎤 Listening → "open Notepad" → 🖥️ Notepad opens → 🔊 "Opening Notepad."
```

Manual:
```powershell
python -m app.main --manual
```

### Supported Commands (one per utterance)

```
Open app:
  open Notepad / open Brave / launch Chrome / start Calculator / run VS Code / open File Explorer

Open website:
  open YouTube / go to GitHub / open Google / launch Gmail

Type:
  type Hello World   → literally types

Keys:
  press Enter / press Escape / press Tab / press Space

Hotkeys:
  press Control C / press Control V / press Control A / press Control Z / press Alt Tab / press Windows D

Mouse:
  click / double click / right click / scroll up / scroll down

Friendly:
  hello → Hello! I'm Nova. / how are you → I'm doing great...
```

Multi-step rejected:
```
"open Brave, go to YouTube and play" → "I can handle one basic action at a time right now."
```

Unknown:
```
"do something complicated" → "I can't perform that action yet."
```

Dangerous blocked, no shell execution.

---

## Project Structure

```
nova/
├── app/
│   ├── main.py              # State machine, PC integration
│   ├── config.py            # Whisper+TTS+Wake+PC .env
│   ├── speech/transcriber.py
│   ├── tts/speaker.py
│   ├── wakeword/detector.py
│   └── pc/                  # NEW Phase 4
│       ├── __init__.py
│       ├── controller.py    # PCController (allowlisted)
│       └── actions.py       # handle_command router
├── .env.example
├── requirements.txt
└── README.md
```

---

## Privacy / Safety

- STT/TTS/wake local, PC actions allowlisted, no `shell=True` with user text, audio in RAM only, no recordings, no cloud.

---

## Roadmap

- [x] Phase 1 STT
- [x] Phase 2 TTS
- [x] Phase 3 Wake Word
- [x] Phase 4 Basic PC Control (current)
- [ ] Phase 5+ LLM, vision, multi-step agent

## License

MIT
