# Nova

Hands-free PC voice assistant (Windows).

## Current Phase

**Phase 5 — Natural Language Command Understanding**

```
👂 "Hey Nova"
      ↓
🎤 Listening (no ENTER)
      ↓
📝 STT (faster-whisper, local, only after wake)
      ↓
┌──────────────┐
│ Fast Router  │── Known ("open Brave") → Execute locally (no LLM)
└──────┬───────┘
       │ Unknown ("Could you bring up Brave?")
       ▼
   LLM interpreter → validated JSON → PC Controller → TTS
```

Fast = immediate, LLM = only when needed. Structured actions only, never shell/code. Offline fallback keeps simple commands working if LLM unavailable.

---

## Features

### Phase 1-2: STT + TTS
- Mic detection, 16kHz, `faster-whisper`; `pyttsx3` SAPI5

### Phase 3: Wake Word
- `vosk` `hey nova` (dummy fallback), state machine, cooldown, `winsound` beep, `--manual`

### Phase 4: PC Control
- Apps `brave/chrome/notepad/calc/vscode/explorer`, websites `youtube/github/google…`, type, keys `enter/esc/tab/space`, hotkeys allowlisted `ctrl+c/v/a/z`, mouse `click/double/right/scroll`

### Phase 5 — Natural Language (new)
- **Natural variations:** `"Can you launch my Brave browser?"` → `open_application brave`; `"Take me to YouTube"` → `open_url youtube`; `"Write hello world"` → `type_text`
- **LLM abstraction:** `app/ai/interpreter.py` `CommandInterpreter` (provider `openai`, model `gpt-4o-mini`), timeout `LLM_TIMEOUT_SECONDS`
- **Strict schema:** `app/ai/schemas.py` `AllowedActions` + `validate_action()` (application/website/key/hotkey/scroll allowlisted)
- **System prompt:** `app/ai/prompts.py` — instructs LLM to output JSON only, one safe action, clarification/unsupported handling, no code generation
- **Fast path:** `open Brave` handled locally without LLM; `Could you bring up browser I usually use?` → LLM
- **Safety:** `app/pc/actions.py` `execute_structured_action()` allowlisted, never `eval/exec/os.system`, validator before `PCController`
- **Multi-step/unsupported:** `unsupported` → `"I can't perform that action yet."` ; ambiguous → `clarification` → `"Which browser…?"`
- **Privacy/Security:** only transcribed text sent to LLM when needed, no audio/screenshots/files, API key in `.env` (gitignored)
- **Failure handling:** timeout/rate-limit/invalid JSON → `"I couldn't process..."`, local commands still work

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

Vosk model auto-downloads or extract to `models/vosk-model-small-en-us-0.15`.

Configure LLM (optional):
```powershell
copy .env.example .env
notepad .env
# Set:
# LLM_ENABLED=true
# LLM_PROVIDER=openai
# LLM_MODEL=gpt-4o-mini
# LLM_API_KEY=sk-...
# LLM_TIMEOUT_SECONDS=10
```

Without API key, Nova still works fully for exact/simple commands via fast router. Natural variations require LLM.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `base` | whisper |
| `TTS_ENABLED` | `true` |  |
| `WAKE_WORD_ENABLED` | `true` |  |
| `PC_CONTROL_ENABLED` | `true` |  |
| `LLM_ENABLED` | `false` | Enable natural language LLM |
| `LLM_PROVIDER` | `openai` |  |
| `LLM_MODEL` | `gpt-4o-mini` | or `gpt-4o` etc. |
| `LLM_API_KEY` | _(none)_ | **never commit** |
| `LLM_TIMEOUT_SECONDS` | `10` | 1–60 |

---

## Usage

Hands-free:
```powershell
python -m app.main
# 👂 Waiting for "hey nova"...
# Hey Nova → "Could you start Brave for me?" → Opening Brave.
```

Manual:
```powershell
python -m app.main --manual
```

Supported natural examples (via LLM):

```
"Could you start Brave for me?" → open_application brave
"Bring up the Brave browser." → open_application brave
"Take me to YouTube" → open_url youtube
"Write hello world here" → type_text hello world
"Could you press Control C?" → hotkey ctrl+c
"Scroll down please" → scroll
"Open my browser." → clarification "Which browser should I open?" (if ambiguous)
"Delete all files" → unsupported → I can't perform that action yet.
"Open Brave, go to YouTube and play" → unsupported multi-step
```

Simple exact commands bypass LLM:
```
open Brave, open YouTube, type Hello, press Enter
```

---

## Project Structure

```
nova/
├── app/
│   ├── main.py              # fast router + LLM fallback + state machine
│   ├── config.py            # LLM .env
│   ├── speech/transcriber.py
│   ├── tts/speaker.py
│   ├── wakeword/detector.py
│   ├── pc/
│   │   ├── controller.py
│   │   └── actions.py       # + execute_structured_action()
│   └── ai/                  # NEW Phase 5
│       ├── __init__.py
│       ├── interpreter.py   # CommandInterpreter
│       ├── schemas.py       # validate_action()
│       └── prompts.py       # SYSTEM_PROMPT
├── .env.example
├── requirements.txt
└── README.md
```

---

## Privacy / Safety

- Only transcribed text sent to LLM when fast router unknown, truncated to 500 chars, no audio/files
- LLM output validated allowlist before PCController, no code/shell, no arbitrary URLs
- Audio RAM only, no cloud beyond LLM when enabled, .env gitignored

---

## Troubleshooting

| Problem | Fix |
|---|---|
| LLM not available | Set `LLM_ENABLED=true` + `LLM_API_KEY`, `pip install openai` |
| Timeout | Increase `LLM_TIMEOUT_SECONDS`, check internet |
| Natural variations not working | Ensure LLM key valid, check logs `LLM interpreted` |
| Simple commands slow | They use fast path locally — ensure LLM not called for exact "open Brave" |
| `open my browser` ambiguous | Expected clarification response |

---

## Roadmap

- [x] Phase 1 STT
- [x] Phase 2 TTS
- [x] Phase 3 Wake Word
- [x] Phase 4 PC Control
- [x] Phase 5 Natural Language (current)
- [ ] Phase 6+ vision, multi-step

## License

MIT
