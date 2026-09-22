# Nova

Hands-free PC voice assistant (Windows).

## Current Phase

**Phase 2 — Voice Input + Speech-to-Text + Text-to-Speech**

```
Microphone → Record → Speech-to-text → Response → Speak aloud
```

Offline, local, privacy-focused. No cloud services, no LLM.

---

## Features

### Phase 1
- Microphone detection (lists all input devices, auto-selects default)
- Push-to-talk voice recording (16 kHz, mono, float32)
- Local speech-to-text via `faster-whisper`
- Configurable Whisper model (`tiny` / `base` / `small` / ...)
- Handles silence, empty speech, and microphone errors gracefully
- Privacy-focused: audio stays in memory, never written to disk

### Phase 2 (new)
- Local text-to-speech via `pyttsx3` (SAPI5 on Windows, offline)
- TTS engine initialized once and reused (low latency)
- Configurable voice, speaking rate, and volume via `.env`
- Voice listing utility
- Simple local response system (no LLM):
  - `hello` → `Hello! I'm Nova.`
  - `hi` → `Hi! I'm ready.`
  - `how are you` → `I'm doing great. I'm ready for your next command.`
  - `test` → `Voice system is working correctly.`
  - unknown → `I heard you say: ...`
- Graceful TTS failure handling (STT keeps working)
- Interruptible speech (`speaker.stop()`) and clean shutdown

---

## Requirements

- Python 3.11+
- Windows 10/11 (SAPI5 for TTS)
- A working microphone + speakers/headphones
- Internet connection on first run (to download the Whisper model)

---

## Installation

```powershell
cd nova
python -m venv .venv
.venv\Scripts\Activate.ps1
# If blocked: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Configuration

```powershell
copy .env.example .env
notepad .env
```

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `base` | `tiny`, `base`, `small`, `medium`, `large-v3` |
| `WHISPER_DEVICE` | `cpu` | `cpu` or `cuda` |
| `WHISPER_COMPUTE_TYPE` | `int8` | `int8` (CPU), `float16` (CUDA) |
| `SAMPLE_RATE` | `16000` | Audio sample rate (Hz) |
| `MAX_RECORDING_SECONDS` | `15` | Auto-stop after this many seconds |
| `WHISPER_LANGUAGE` | _(auto)_ | Force language e.g. `en` |
| `TTS_ENABLED` | `true` | Enable/disable speech output |
| `TTS_RATE` | `175` | Speaking rate (50–400) |
| `TTS_VOLUME` | `1.0` | Volume 0.0–1.0 |
| `TTS_VOICE` | _(default)_ | Voice ID substring; empty = system default |

List available voices:

```powershell
python -c "from app.tts.speaker import get_available_voices; [print(f'[{i}] {v.name} — {v.id}') for i,v in enumerate(get_available_voices())]"
# or inside Python:
# from app.tts.speaker import Speaker; Speaker().initialize(); Speaker().print_voices()
```

On Windows typical voices: `Microsoft David`, `Microsoft Zira`, `Microsoft Mark`.

---

## Usage

```powershell
python -m app.main
```

Expected startup:

```
Nova Voice Engine
-----------------

Available microphones:
  [0] Microphone (Realtek)
  [1] Headset Microphone

Selected microphone: [0] Microphone

Loading speech recognition model...
Speech recognition ready.

Text-to-speech: Ready

Available voices:
  [0] Microsoft David - English (United States) (HKEY_LOCAL_MACHINE\...)
  [1] Microsoft Zira - English (United States) (...)
  [2] Microsoft Mark - English (United States) (...)

Selected voice: HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_EN-US_ZIRA_11.0

Nova:
"Voice system initialized."

================================
        NOVA VOICE ENGINE
================================

🎤 Microphone: Microphone — READY
📝 Speech recognition: READY (model=base)
🔊 Voice output: READY (rate=175 vol=1.0)

Status: READY

Press ENTER to speak.
Press Q + ENTER to quit.
```

Recording:

```
🎤 LISTENING...
Speak now.

📝 You said:
"Hello Nova"

🔊 Nova:
"Hello! I'm Nova."

Status: READY
```

If TTS fails:

```
WARNING:
Text-to-speech is unavailable.
Voice input will continue to work.
```

---

## Microphone Permissions (Windows)

Settings → Privacy & security → Microphone → Enable *Microphone access* and *Let desktop apps access your microphone*.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `sounddevice` install fails | Use python.org Python, not Windows Store |
| Model download slow | Use `WHISPER_MODEL=tiny` |
| `WHISPER_DEVICE=cuda` fails | Install CUDA toolkit or use `cpu` |
| TTS says `pyttsx3 not installed` | `pip install pyttsx3 comtypes` |
| TTS voice not found | Leave `TTS_VOICE` empty or copy exact ID from voice list |
| No speech detected | Check mic volume in Windows Sound settings |
| TTS silent | Check speaker volume, try different `TTS_VOICE`, check `TTS_ENABLED` |

---

## Project Structure

```
nova/
├── app/
│   ├── __init__.py
│   ├── main.py              # Mic detection, recording loop, responses, TTS integration
│   ├── config.py            # .env configuration (Whisper + TTS)
│   ├── speech/
│   │   ├── __init__.py
│   │   └── transcriber.py   # faster-whisper wrapper (load once)
│   └── tts/
│       ├── __init__.py
│       └── speaker.py       # pyttsx3 wrapper (init once, speak/stop/shutdown)
├── tests/
│   └── __init__.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Privacy

- Audio kept in RAM only, released after transcription.
- No recordings written to disk.
- No audio sent to external services — STT and TTS are fully local.
- No conversation history or database.
- Logs do not contain speech content.

---

## Roadmap

- [x] **Phase 1** — Voice input + speech-to-text
- [x] **Phase 2** — Text-to-speech + voice responses (current)
- [ ] Phase 3 — Wake word, agent, PC control
- [ ] Phase 4 — Browser automation & LLM

---

## License

MIT
