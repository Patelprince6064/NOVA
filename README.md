# Nova

> Nova is a lightweight hands-free Windows voice assistant that can understand natural-language commands and safely control supported PC and browser actions.

Say **"Hey Nova"** — Nova listens, acts, and replies with a short voice. No keyboard needed for everyday tasks.

```
Windows starts → Nova in tray → "Hey Nova" → "Yes?" → "Open Brave" → "Opening Brave."
```

---

## Features

- **Wake word** — `Hey Nova` (Vosk, offline, "hey nova" configurable)
- **Speech recognition** — `faster-whisper` (offline, base/tiny/small)
- **Voice responses** — `pyttsx3` SAPI5 offline, interruptible, single engine
- **PC control** — open apps (Brave/Chrome/Notepad/VS Code/Calculator/Explorer/Edge/Firefox), type, press keys, hotkeys, mouse (allowlisted)
- **Browser control** — Playwright reused session: open URL, search web, YouTube search, back/forward/refresh/scroll/close
- **Natural language** — strict JSON interpreter + fast local router (no LLM for `open Brave / scroll down / stop`)
- **Multi-step tasks** — `open Brave, go to YouTube, search for Arijit Singh, play first result` → validated planner (max 8, no code/shell)
- **Screen understanding** — on-demand screenshot + vision (find element / describe screen) with confidence
- **Conversation mode** — follow-ups without repeating `Hey Nova` (`Go to YouTube` → `Search Arijit Singh` → `Play the first one`) with short-term context only
- **Stop/Cancel** — `Stop / Cancel / Never mind / Shut up` stops TTS and cancels tasks immediately; browser stays open
- **Performance** — models loaded once, silence-based early stop (700ms), LLM/browser/TTS reuse, router ms-level
- **Windows background** — system tray (Ready/Listening/Processing/Speaking/Paused), pause/resume, global hotkeys (`Ctrl+Shift+N` toggle, `Ctrl+Shift+X` stop), optional startup

---

## Requirements

- **Windows** 10/11 (primary)
- **Python 3.11+** for development (3.10+ may work)
- **Microphone + speakers/headphones**
- **Optional** internet + `LLM_API_KEY` for AI natural language / cloud vision; offline mode still supports wake word, STT (if model cached), TTS, PC control
- **Optional** Playwright browser for web tasks (`setup_browser.bat`)

---

## Installation

```powershell
cd nova
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
# Browser (if you use web tasks)
.\setup_browser.bat
# or: playwright install chromium
```

**Configure**
```powershell
copy .env.example .env
# edit .env — set LLM_API_KEY if you want AI, else leave LLM_ENABLED=false
notepad .env
```

**Run**
```powershell
python run.py
# single entry point — or: python -m app.main / python -m app.main --manual
```

First run shows:
```
=================================
        NOVA ASSISTANT
=================================
Microphone       ✓
Speaker          ✓
Speech Model     ✓
Wake Word        ✓
TTS              ✓
PC Control       ✓
Browser          ✓
AI               ✓
Nova is ready.
```

Say **"Hey Nova"** → wait for listening → speak command.

---

## Usage

**Apps**
```text
Hey Nova, open Brave.
Hey Nova, open Notepad.
Hey Nova, open VS Code.
Hey Nova, open Calculator.
Hey Nova, open File Explorer.
```

**Browser**
```text
Hey Nova, open YouTube.
Hey Nova, go to Google.
Hey Nova, search Python tutorials.
Hey Nova, go back.
Hey Nova, refresh.
```

**PC**
```text
Hey Nova, type hello world.
Hey Nova, press Enter.
Hey Nova, scroll down.
Hey Nova, scroll up.
```

**Conversation (no repeat wake)**
```text
Hey Nova
Open Brave.
Go to YouTube.
Search Arijit Singh.
Play the first one.
```

**Cancellation / Follow-up**
```text
Stop.
Cancel.
Never mind.
Do that again.
Try again.
Go back.
```

Tray: right-click icon → `Pause Listening / Resume / Test Voice / Open Logs / Settings / Restart / Exit`.

Hotkeys (if `GLOBAL_HOTKEY_ENABLED=true`): `Ctrl+Shift+N` toggle, `Ctrl+Shift+X` stop.

---

## Configuration

All in `app/config.py` + `.env` (sensible defaults). Key vars:

| Variable | Default | Description |
|---|---|---|
| `NOVA_NAME` | `Nova` | Display name |
| `WAKE_WORD_ENABLED` | `true` | Hands-free wake |
| `WAKE_WORD` | `hey nova` | Phrase |
| `CONVERSATION_MODE_ENABLED` | `true` | Follow-ups without wake |
| `CONVERSATION_TIMEOUT_SECONDS` | `8` | Reset after silence |
| `PC_CONTROL_ENABLED` | `true` | Allow apps/keys/mouse |
| `BROWSER_ENABLED` | `true` | Playwright |
| `BROWSER_HEADLESS` | `false` | Visible browser |
| `VISION_ENABLED` | `true` | Screen analysis |
| `AGENT_ENABLED` | `true` | Multi-step planner |
| `LLM_ENABLED` | `true` | Needs `LLM_API_KEY` |
| `LLM_PROVIDER` | `openai` | |
| `PERFORMANCE_DEBUG` | `false` | Prints timing dashboard |
| `LOG_LEVEL` | `INFO` | DEBUG/INFO/WARNING |
| `LOG_MAX_MB` | `5` | Rotation size |
| `START_WITH_WINDOWS` | `false` | Opt-in Startup folder |
| `START_MINIMIZED` | `true` | |
| `START_IN_TRAY` | `true` | |
| `GLOBAL_HOTKEY_ENABLED` | `false` | Needs `keyboard` |
| `WHISPER_MODEL` | `base` | tiny/base/small |
| `TTS_RATE` | `175` | |
| `SILENCE_TIMEOUT_MS` | `700` | Early stop |
| `MIN_SPEECH_DURATION_MS` | `250` | |

See `.env.example` for full list.

---

## Troubleshooting

**Microphone unavailable**
- Windows Settings → Privacy & security → Microphone → Allow access → let desktop apps access
- Check `logs/nova.log`; run `python -m app.health.checker` (health JSON)

**TTS not working**
- `pip install pyttsx3 comtypes pywin32` (Windows SAPI5)
- Check `TTS_ENABLED=true` and `python -c "from app.tts.speaker import get_available_voices; print(get_available_voices())"`

**Wake word not detecting**
- Install vosk model: `pip install vosk` + download `vosk-model-small-en-us-0.15.zip` to `models/` (auto-download tries)
- Dummy energy detector works but less accurate

**Browser not starting**
- `.\setup_browser.bat` or `playwright install chromium`
- Check `BROWSER_ENABLED=true` and `logs/errors.log`

**AI unavailable**
- Set `LLM_API_KEY` in `.env` and `LLM_ENABLED=true` (`openai` provider)
- Offline: local commands (`open Brave`, `scroll down`) still work

**Playwright browser missing in packaged app**
- Packaged `Nova.exe` does not bundle browsers; on target machine run `setup_browser.bat` once

**Packaged app not starting**
- Run `dist/Nova/Nova.exe` from `cmd` to see error, check `logs/`, ensure `.env` beside exe
- For windowed build, check Event Viewer or run `Nova.exe --debug` (console)

**Vision not working**
- `VISION_ENABLED=true` + `VISION_API_KEY` or `LLM_API_KEY` + `mss` + `Pillow`

---

## Project Structure

```
nova/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── logging_setup.py
│   ├── speech/transcriber.py
│   ├── tts/speaker.py
│   ├── wakeword/detector.py
│   ├── pc/{controller,actions}.py
│   ├── ai/{interpreter,schemas,prompts}.py
│   ├── browser/{controller,actions,sites}.py
│   ├── vision/{screenshot,analyzer,schemas}.py
│   ├── agent/{planner,executor,validator,schemas}.py
│   ├── conversation/{manager,context,state}.py
│   ├── interrupt/{manager,detector,events}.py
│   ├── performance/{timer,metrics}.py
│   ├── tray/tray.py
│   ├── hotkey/controller.py
│   ├── startup/windows.py
│   └── health/checker.py
├── tests/
├── assets/nova.ico
├── logs/ (created at runtime)
├── models/ (whisper/vosk cache)
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py
├── build_windows.bat
├── setup_browser.bat
└── README.md
```

---

## Build Windows Executable

```powershell
pip install pyinstaller pillow pystray keyboard pywin32
.\build_windows.bat
# → dist/Nova/Nova.exe
```

PyInstaller bundles Python + deps (one-dir, windowed, icon `assets/nova.ico`). First startup still needs Whisper/vosk model download and `setup_browser.bat` for Playwright.

**Setup startup (opt-in):** set `START_WITH_WINDOWS=true` in `.env` or Tray → Startup (creates `AppData\...\Startup\Nova.bat` → `pythonw run.py`, no admin).

---

## Performance

- Whisper/TTS/Browser/Vision/AI clients loaded once, reused
- Fast local router (ms) before LLM; LLM only for natural language
- Silence early-stop 700ms, no fixed long sleeps, condition-based browser waits
- In-memory metrics (`PERFORMANCE_DEBUG=true` prints dashboard)
- Benchmark: `python -m app.performance.metrics` (local avg ~0.02s router, total ~0.04s simulated)

---

## Privacy / Safety

- Audio RAM only, screenshots on-demand, no permanent recordings/screenshots
- No passwords/tokens/API keys logged or stored; `.env` git-ignored
- Allowlist validation (`APPLICATION_ALIASES`, `WEBSITE_ALIASES`, `ALLOWED_HOTKEYS`, `validate_plan`); no `eval/exec/os.system/subprocess(shell=True)` for voice/AI
- Conversation context short-term only, capped 10 turns, no sensitive data
- No telemetry

## License

MIT
