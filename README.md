# Nova — Hands-Free Windows Voice Assistant

<p align="center">
  <strong>Control your PC with your voice. No keyboard. No clicks. Just say “Hey Nova.”</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Windows 10/11" />
  <img src="https://img.shields.io/badge/Offline-Capable-10B981?style=flat-square" alt="Offline Capable" />
  <img src="https://img.shields.io/badge/License-MIT-111827?style=flat-square" alt="MIT License" />
  <img src="https://img.shields.io/badge/STT-faster--whisper-FF6B35?style=flat-square" alt="faster-whisper" />
  <img src="https://img.shields.io/badge/TTS-SAPI5%20pyttsx3-6366F1?style=flat-square" alt="TTS" />
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#features">Features</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#usage">Usage</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#project-structure">Project Structure</a> •
  <a href="#build--distribution">Build</a>
</p>

---

> **Nova** is a lightweight, privacy-first Windows voice assistant that runs locally. It understands natural language, controls your PC and browser hands-free, executes multi-step tasks, sees your screen on demand, and replies with natural offline voice — all without sending your audio to the cloud by default.

```
Windows starts → Nova in tray → "Hey Nova" → "Yes?" → "Open Brave" → "Opening Brave."
```

### Why Nova?

- **Offline-first** — Wake word (Vosk), transcription (faster-whisper), and voice (SAPI5) all run locally.
- **Fast** — Millisecond local router handles common commands without any LLM call.
- **Safe** — Allowlist-only actions, no `eval`/`exec`/shell, screenshots only on demand.
- **Hands-free** — Follow-up conversation without repeating the wake word, plus instant `Stop / Cancel`.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Website](#website)
- [Build & Distribution](#build--distribution)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Privacy & Security](#privacy--security)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

| Capability | Details |
|---|---|
| **Wake Word** | `Hey Nova` — offline Vosk detection, configurable phrase, threshold & cooldown |
| **Speech-to-Text** | `faster-whisper` (tiny / base / small / medium) — int8 on CPU, float16 on CUDA |
| **Text-to-Speech** | `pyttsx3` SAPI5 — interruptible, single engine, no overlapping speech |
| **PC Control** | Open apps (Brave, Chrome, Notepad, VS Code, Calculator, Explorer, Edge, Firefox), type, press keys, hotkeys, scroll |
| **Browser Control** | Playwright reused session — open URL, web search, YouTube search, back/forward/refresh/scroll/close |
| **Natural Language** | Strict JSON interpreter + fast local router — `open Brave` never hits LLM |
| **Multi-Step Agent** | `open Brave, go to YouTube, search for Arijit Singh, play first result` → validated planner (max 8 steps, retries, timeout) |
| **Screen Understanding** | On-demand screenshot + vision (find element / describe screen) with confidence threshold |
| **Conversation Mode** | Follow-ups without wake word (`Go to YouTube` → `Search Arijit Singh` → `Play the first one`) — 8s timeout, 10-turn cap |
| **Interruption** | `Stop / Cancel / Never mind / Shut up` stops TTS and cancels tasks instantly; browser stays open |
| **Windows Integration** | System tray (Ready/Listening/Processing/Speaking/Paused), pause/resume, global hotkeys, optional Startup launch |
| **Performance** | Models loaded once, 700ms silence early-stop, LLM/browser/TTS reuse, in-memory metrics dashboard |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Core** | Python 3.11+, `app/config.py` centralized config (frozen dataclass) |
| **Audio In** | `sounddevice`, `numpy`, `faster-whisper` |
| **Audio Out** | `pyttsx3` + `comtypes` + `pywin32` (SAPI5) |
| **Wake Word** | `vosk` (auto-download `vosk-model-small-en-us-0.15` to `models/`) |
| **Automation** | `pyautogui`, `pywin32`, `keyboard` |
| **Browser** | `playwright` (chromium), reused session |
| **Vision** | `mss` + `Pillow` + OpenAI vision API (optional) |
| **AI** | `openai` (optional — local router works offline) |
| **Desktop** | `pystray`, `Pillow`, Windows Startup folder |
| **Packaging** | `PyInstaller` (one-dir, windowed, `assets/nova.ico`) |
| **Website** | React 19 + Vite 8 + Tailwind CSS 4 + Framer Motion 13 |
| **Testing** | `pytest` — `tests/test_phase{9,10,11}_*.py`, `test_long_run.py` |

---

## Architecture

```
                          ┌─────────────────────┐
                          │   System Tray +     │
                          │  Global Hotkeys     │
                          └─────────┬───────────┘
                                    │
  ┌──────────┐  wake   ┌────────────▼────────────┐  STT  ┌──────────────────┐
  │ Microphone├───────►│  WakeWordDetector (Vosk)├──────►│ Transcriber      │
  └──────────┘        └────────────┬────────────┘       │ (faster-whisper) │
                                   │ command             └────────┬─────────┘
                          ┌────────▼────────┐                     │
                          │  PerfTimer /    │              ┌──────▼──────┐
                          │  Metrics        │              │   Router    │
                          └────────┬────────┘              │  (fast)     │
                                   │                       └──────┬──────┘
                          ┌────────▼────────┐              ┌──────▼──────┐
                          │  Conversation   │◄─────────────┤  AI / LLM   │
                          │  Manager +      │  context     │ Interpreter │
                          │  Interrupt Mgr  │              └──────┬──────┘
                          └────────┬────────┘                     │
                    ┌──────────────┼──────────────┐               │
                    ▼              ▼              ▼               ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐    ┌─────────────┐
              │ PC       │  │ Browser  │  │ Vision   │    │ Agent       │
              │Controller│  │Controller│  │ Analyzer │    │ Planner+Exec│
              └────┬─────┘  └────┬─────┘  └────┬─────┘    └──────┬──────┘
                   │             │             │                 │
                   └─────────────┼─────────────┼─────────────────┘
                                 ▼             ▼
                          ┌─────────────────────────┐
                          │   Speaker (pyttsx3)     │
                          │   + Health Checker      │
                          └─────────────────────────┘
```

**Request flow:**

1. `LISTENING_FOR_WAKE_WORD` — Vosk listens for `Hey Nova`
2. `LISTENING_FOR_COMMAND` — `record_command_auto()` captures with 700ms silence early-stop
3. `PROCESSING` — `PerfTimer` → local router (vision → browser → PC) → if unknown and LLM available → `CommandInterpreter` → `validate_plan`
4. `EXECUTING` — `TaskExecutor` runs allowlisted steps sequentially with verify/retry/timeout/cancel
5. `SPEAKING` — `Speaker.speak()` with TTS suppression (wake word paused + cooldown)

> Screenshots are **only** captured on the vision path. Normal commands never capture the screen.

---

## Requirements

| Requirement | Notes |
|---|---|
| **OS** | Windows 10 / 11 (primary target) |
| **Python** | 3.11+ recommended (3.10+ may work) |
| **Hardware** | Microphone + speakers/headphones; 4GB+ RAM recommended for `base` model |
| **Network** | Optional — offline mode works for wake word, STT (if model cached), TTS, PC control |
| **API Key** | Optional `LLM_API_KEY` for natural language & cloud vision — set `LLM_ENABLED=false` to run fully offline |
| **Browser** | Optional Playwright Chromium (`setup_browser.bat`) for web tasks |

---

## Quick Start

### 1. Clone & Install

```powershell
git clone <your-repo-url> nova
cd nova

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Browser (for web tasks)

```powershell
.\setup_browser.bat
# equivalent: playwright install chromium
```

### 3. Configure

```powershell
copy .env.example .env
notepad .env
# Set LLM_API_KEY if you want AI features, otherwise leave LLM_ENABLED=false
```

### 4. Run

```powershell
python run.py
# alternatives: python -m app.main  or  python -m app.main --manual
```

First run prints a health dashboard:

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

Say **“Hey Nova”** → wait for the beep / `LISTENING` → speak your command.

> **Manual mode** (no wake word, press Enter to record): `python -m app.main --manual`

---

## Usage

### App Control

```text
Hey Nova, open Brave.
Hey Nova, open Notepad.
Hey Nova, open VS Code.
Hey Nova, open Calculator.
Hey Nova, open File Explorer.
```

### Browser

```text
Hey Nova, open YouTube.
Hey Nova, go to Google.
Hey Nova, search Python tutorials.
Hey Nova, go back.
Hey Nova, refresh.
Hey Nova, scroll down.
```

### PC

```text
Hey Nova, type hello world.
Hey Nova, press Enter.
Hey Nova, scroll down.
Hey Nova, scroll up.
```

### Multi-Step (Agent)

```text
Hey Nova, open Brave, go to YouTube, search for Arijit Singh, play first result.
Hey Nova, play daylight song on YouTube.
Hey Nova, open Brave and search for Python tutorials.
```

### Conversation (no repeat wake word)

```text
Hey Nova
→ Open Brave.
→ Go to YouTube.
→ Search Arijit Singh.
→ Play the first one.
```

### Screen Understanding

```text
Hey Nova, what is on my screen?
Hey Nova, where is the YouTube search box?
Hey Nova, what application is open?
```

### Cancellation & Follow-up

```text
Stop.
Cancel.
Never mind.
Shut up.
Do that again. / Try again.
Go back.
```

**Tray:** Right-click icon → `Pause Listening / Resume / Test Voice / Open Logs / Settings / Restart / Exit`.

**Hotkeys** (when `GLOBAL_HOTKEY_ENABLED=true`): `Ctrl+Shift+N` toggle listening, `Ctrl+Shift+X` stop.

---

## Configuration

All settings live in `app/config.py` + `.env` (sensible defaults, clamped to safe ranges). See `.env.example` for the full list.

| Variable | Default | Description |
|---|:---:|---|
| `NOVA_NAME` | `Nova` | Display name |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `WHISPER_MODEL` | `base` | `tiny` / `base` / `small` / `medium` / `large-v3` |
| `WHISPER_DEVICE` | `cpu` | `cpu` or `cuda` |
| `WHISPER_COMPUTE_TYPE` | `int8` | `int8` (CPU) / `float16` (CUDA) |
| `TTS_ENABLED` | `true` | Enable voice responses |
| `TTS_RATE` | `175` | 50–400 |
| `TTS_VOLUME` | `1.0` | 0.0–1.0 |
| `WAKE_WORD_ENABLED` | `true` | Hands-free wake word |
| `WAKE_WORD` | `hey nova` | Trigger phrase |
| `WAKE_WORD_THRESHOLD` | `0.5` | 0.0–1.0 |
| `COMMAND_TIMEOUT_SECONDS` | `6` | 1–30s |
| `PC_CONTROL_ENABLED` | `true` | Allow apps/keys/mouse |
| `BROWSER_ENABLED` | `true` | Playwright |
| `BROWSER_HEADLESS` | `false` | Visible browser |
| `VISION_ENABLED` | `true` | Screen analysis |
| `VISION_MIN_CONFIDENCE` | `0.70` | 0.0–1.0 |
| `AGENT_ENABLED` | `true` | Multi-step planner |
| `MAX_TASK_STEPS` | `8` | 1–20 |
| `CONVERSATION_MODE_ENABLED` | `true` | Follow-ups without wake word |
| `CONVERSATION_TIMEOUT_SECONDS` | `8` | 3–30s |
| `INTERRUPTION_ENABLED` | `true` | Stop/cancel handling |
| `SILENCE_TIMEOUT_MS` | `700` | 200–2000ms — early stop after speech |
| `MIN_SPEECH_DURATION_MS` | `250` | 100–1000ms |
| `PERFORMANCE_DEBUG` | `false` | Prints timing dashboard |
| `START_WITH_WINDOWS` | `false` | Opt-in Startup folder |
| `GLOBAL_HOTKEY_ENABLED` | `false` | Requires `keyboard` |
| `LLM_ENABLED` | `false` | Needs `LLM_API_KEY` |
| `LLM_PROVIDER` | `openai` | `openai` |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |

```powershell
# Find available TTS voices
python -c "from app.tts.speaker import get_available_voices; [print(v.name, v.id) for v in get_available_voices()]"
```

---

## Project Structure

```
nova/
├── app/
│   ├── main.py                      # Hands-free loop + routing + conversation
│   ├── config.py                    # Frozen dataclass — single source of truth
│   ├── logging_setup.py             # Rotating file + console logging
│   ├── speech/transcriber.py        # faster-whisper wrapper (loaded once)
│   ├── tts/speaker.py               # SAPI5 pyttsx3 — interruptible, thread-safe
│   ├── wakeword/detector.py         # Vosk wake word + energy fallback
│   ├── pc/
│   │   ├── controller.py            # App launch, window, foreground detection
│   │   └── actions.py               # Allowlisted router + execute_structured_action
│   ├── browser/
│   │   ├── controller.py            # Playwright reused session
│   │   ├── actions.py               # Fast browser router
│   │   └── sites.py                 # URL helpers (google_search_url, youtube_search_url)
│   ├── ai/
│   │   ├── interpreter.py           # Strict JSON LLM interpreter
│   │   ├── schemas.py               # Validated action schemas
│   │   └── prompts.py               # System prompts
│   ├── vision/
│   │   ├── screenshot.py            # mss capture, resize to max 1600x1000
│   │   ├── analyzer.py              # ScreenAnalyzer (on-demand)
│   │   └── schemas.py               # FindResult, analysis types
│   ├── agent/
│   │   ├── planner.py               # Multi-step TaskPlanner (max 8, no code/shell)
│   │   ├── executor.py              # Sequential executor — verify, retry, timeout, cancel
│   │   ├── validator.py             # validate_plan — allowlist enforcement
│   │   └── schemas.py               # Task / step schemas
│   ├── conversation/
│   │   ├── manager.py               # ConversationManager — short-term context
│   │   ├── context.py               # Context store (capped 10 turns, no sensitive data)
│   │   ├── state.py                 # ConversationState
│   │   └── router.py                # resolve_follow_up — pronoun & fast phrase routing
│   ├── interrupt/
│   │   ├── manager.py               # InterruptManager
│   │   ├── detector.py              # is_stop_command / is_retry_command
│   │   └── events.py                # Global stop event
│   ├── performance/
│   │   ├── timer.py                 # PerfTimer — per-stage latency
│   │   └── metrics.py               # global_metrics + benchmark
│   ├── tray/tray.py                 # pystray — Ready/Listening/Processing/Speaking/Paused
│   ├── hotkey/controller.py         # Global hotkeys (Ctrl+Shift+N / Ctrl+Shift+X)
│   ├── startup/windows.py           # Startup folder sync (no admin)
│   └── health/checker.py            # run_health_check / print_health
├── website/                         # Marketing site — React 19 + Vite 8 + Tailwind 4
│   ├── src/components/              # Navbar, Hero, FeatureGrid, VoiceDemo, etc.
│   ├── public/ & dist/
│   └── package.json
├── tests/
│   ├── test_phase9_conversation.py
│   ├── test_phase10_interruption.py
│   ├── test_phase11_performance.py
│   └── test_long_run.py
├── assets/nova.ico
├── logs/                            # Created at runtime (git-ignored)
├── models/                          # Whisper / Vosk cache (git-ignored)
├── .env.example                     # All tunable vars with defaults
├── requirements.txt
├── run.py                           # Single entry point — config → health → app.main
├── build_windows.bat                # PyInstaller one-dir build
├── setup_browser.bat                # Playwright chromium install
└── README.md
```

---

## Website

The marketing site lives in `website/` — React 19 + Vite + Tailwind CSS 4 + Framer Motion.

```powershell
cd website
npm install
npm run dev      # http://localhost:5173
npm run build    # → website/dist
npm run preview
```

| Script | Description |
|---|---|
| `npm run dev` | Vite dev server with HMR |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Preview production build locally |
| `npm run lint` | Oxlint |

---

## Build & Distribution

### Windows Executable (PyInstaller)

```powershell
pip install pyinstaller pillow pystray keyboard pywin32
.\build_windows.bat
# → dist/Nova/Nova.exe  (one-dir, windowed, icon assets/nova.ico)
```

- Bundles Python + dependencies; does **not** bundle Playwright browsers — run `setup_browser.bat` once on the target machine.
- First launch still downloads Whisper / Vosk models on demand to `models/`.
- Run `dist/Nova/Nova.exe` from `cmd` to see errors; check `logs/errors.log` for windowed builds.

### Startup (opt-in, no admin)

Set `START_WITH_WINDOWS=true` in `.env` or use **Tray → Startup**. Creates `AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Nova.bat` → `pythonw run.py`.

---

## Development

### Logging

```powershell
# Tail logs
Get-Content logs/nova.log -Tail 50 -Wait
Get-Content logs/errors.log -Tail 50 -Wait
```

- Rotating logs: `LOG_MAX_MB=5` (1–50), `LOG_BACKUP_COUNT=3` (1–10)
- Set `LOG_LEVEL=DEBUG` and `PERFORMANCE_DEBUG=true` for timing dashboard

### Health Check

```powershell
python -m app.health.checker
# JSON: microphone, speaker, speech model, wake word, TTS, PC, browser, AI, vision
```

### Benchmarks

```powershell
python -m app.performance.metrics
# Local avg: router ~0.02s, total ~0.04s (simulated, no LLM)
```

### Tests

```powershell
pip install pytest
pytest -v
pytest tests/test_phase11_performance.py -v
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| **Microphone unavailable** | Windows Settings → Privacy & security → Microphone → Allow access → let desktop apps access. Check `logs/nova.log` and `python -m app.health.checker`. |
| **TTS not working** | `pip install pyttsx3 comtypes pywin32` (SAPI5). Check `TTS_ENABLED=true`. Test: `python -c "from app.tts.speaker import get_available_voices; print(get_available_voices())"` |
| **Wake word not detecting** | `pip install vosk` + download `vosk-model-small-en-us-0.15.zip` to `models/` (auto-download tries). Energy fallback still works but less accurate. |
| **Browser not starting** | `.\setup_browser.bat` or `playwright install chromium`. Check `BROWSER_ENABLED=true` and `logs/errors.log`. |
| **AI unavailable** | Set `LLM_API_KEY` in `.env` and `LLM_ENABLED=true`. Offline local commands (`open Brave`, `scroll down`) still work. |
| **Playwright missing in packaged app** | Packaged `Nova.exe` does not bundle browsers — run `setup_browser.bat` once on target. |
| **Packaged app not starting** | Run `dist/Nova/Nova.exe` from `cmd` to see error. Ensure `.env` beside exe. For windowed build, check Event Viewer or `Nova.exe --debug`. |
| **Vision not working** | `VISION_ENABLED=true` + `VISION_API_KEY` or `LLM_API_KEY` + `mss` + `Pillow`. |
| **Hotkeys not working** | `GLOBAL_HOTKEY_ENABLED=true` and `pip install keyboard`. Run as normal user (no admin needed). |

---

## Privacy & Security

- **Audio** — RAM only, never written to disk; no `*.wav` committed (git-ignored).
- **Screenshots** — On-demand only (vision path), never continuous monitoring, not persisted.
- **No telemetry** — Zero external tracking.
- **Secrets** — `.env` is git-ignored; API keys / passwords are never logged or stored in context.
- **Allowlist enforcement** — `APPLICATION_ALIASES`, `WEBSITE_ALIASES`, `ALLOWED_HOTKEYS`, `validate_plan` — no `eval` / `exec` / `os.system` / `subprocess(shell=True)` for voice/AI.
- **Context** — Short-term only, capped 10 turns, no sensitive data, in-memory.
- **Validation** — All LLM output is strict JSON validated before execution; unsupported actions return a safe message.

---

## Roadmap

- [ ] System-wide dictation mode
- [ ] Custom wake word training
- [ ] Plugin API for user-defined actions
- [ ] macOS / Linux support (audio + TTS abstraction)
- [ ] On-device LLM (no API key required)
- [ ] Signed installer (MSIX / Inno Setup)

---

## Contributing

Contributions are welcome!

1. Fork the repo and create a feature branch (`git checkout -b feat/my-feature`)
2. Make changes and add tests under `tests/`
3. Run `pytest -v` and ensure health check passes (`python -m app.health.checker`)
4. Commit with a clear message and open a PR

Please avoid committing `.env`, `logs/`, `models/`, `*.wav`, or `dist/` (all git-ignored).

---

## License

[MIT](LICENSE) — free for personal and commercial use.

---

<p align="center">
  Built with care for hands-free computing. Say <strong>“Hey Nova”</strong> and get things done.
</p>
