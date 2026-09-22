# Nova

Hands-free PC voice assistant (Windows).

## Current Phase

**Phase 3 — Hands-Free Wake Word**

```
  👂 Waiting for "Hey Nova"
           ↓
  🎤 Listening (auto, no ENTER)
           ↓
  📝 Speech-to-text (local faster-whisper, only after wake)
           ↓
  🔊 Voice response (local pyttsx3)
           ↓
  👂 Waiting again
```

Fully hands-free, offline, privacy-focused. No cloud, no LLM.

---

## Features

### Phase 1
- Microphone detection, push-to-talk recording (16 kHz mono), local STT via `faster-whisper`

### Phase 2
- Local TTS via `pyttsx3` (SAPI5), configurable voice/rate/volume, simple responses

### Phase 3 (new)
- Hands-free wake-word detection — say **"Hey Nova"** without touching keyboard
- Local wake-word engine (Vosk with `vosk-model-small-en-us-0.15`, fallback dummy energy detector — no cloud)
- State machine: `IDLE → LISTENING_FOR_WAKE_WORD → LISTENING_FOR_COMMAND → PROCESSING → SPEAKING → LISTENING_FOR_WAKE_WORD`
- Audio Input Manager: single mic ownership, wake mode pauses during command/TTS
- Wake sound beep (configurable `WAKE_SOUND_ENABLED`, short `winsound.Beep`)
- Command timeout `COMMAND_TIMEOUT_SECONDS` (default 8s) + silence handling
- False-activation threshold `WAKE_WORD_THRESHOLD` + cooldown `WAKE_WORD_COOLDOWN_MS` to avoid TTS echo
- TTS echo prevention: detection paused during `SPEAKING`
- Backward compatible manual mode: `python -m app.main --manual` (ENTER loop)

---

## Requirements

- Python 3.11+, Windows 10/11, mic + speakers, internet first run for Whisper

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

Wake-word model (for accurate "Hey Nova" phrase):
- Auto-download on first run (40MB) or manually:
```powershell
pip install vosk
# Download https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
# Extract to nova/models/vosk-model-small-en-us-0.15
# Verify: dir models\vosk-model-small-en-us-0.15\am\final.mdl exists
```
Without the model, Nova falls back to dummy energy detector (any loud speech triggers — less accurate but still hands-free).

---

## Configuration

```powershell
copy .env.example .env
notepad .env
```

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `base` | `tiny`/`base`/`small`/`medium`/`large-v3` |
| `WHISPER_DEVICE` | `cpu` | `cpu` or `cuda` |
| `WHISPER_COMPUTE_TYPE` | `int8` | `int8`/`float16` |
| `SAMPLE_RATE` | `16000` | Hz |
| `MAX_RECORDING_SECONDS` | `15` | Manual mode auto-stop |
| `TTS_ENABLED` | `true` | Enable TTS |
| `TTS_RATE` | `175` | 50–400 |
| `TTS_VOLUME` | `1.0` | 0.0–1.0 |
| `TTS_VOICE` | _(default)_ | Voice ID substring |
| `WAKE_WORD_ENABLED` | `true` | Enable hands-free |
| `WAKE_WORD` | `hey nova` | Phrase (lowercase) |
| `WAKE_WORD_THRESHOLD` | `0.5` | 0.0–1.0 sensitivity (Vosk: unused, dummy: energy) |
| `COMMAND_TIMEOUT_SECONDS` | `8` | 1–30 s wait after wake |
| `WAKE_SOUND_ENABLED` | `true` | Beep on wake |
| `WAKE_WORD_COOLDOWN_MS` | `500` | 0–5000 ms ignore after trigger/TTS |

List TTS voices:
```powershell
python -c "from app.tts.speaker import get_available_voices; [print(f'[{i}] {v.name} — {v.id}') for i,v in enumerate(get_available_voices())]"
```

---

## Usage

Hands-free (default):
```powershell
python -m app.main
# 👂 Waiting for "hey nova"...
# Say: Hey Nova
# 🎤 Listening... -> speak command -> Nova responds -> waiting again
# Q + ENTER or Ctrl+C to quit
```

Manual (Phase 1/2 compat):
```powershell
python -m app.main --manual
# Press ENTER to record
```

Startup shows:
```
Wake-word backend: vosk (or dummy)
👂 Waiting for "hey nova"...
```

On wake:
```
✨ Wake word detected: "hey nova"
🔔
🎤 LISTENING... Speak now
📝 You said: "hello"
🔊 Nova: "Hello! I'm Nova."
👂 Waiting for "hey nova"...
```

Silence timeout:
```
🎤 Listening...
⚠️ No command detected.
👂 Waiting for "hey nova"...
```

---

## Microphone Permissions

Settings → Privacy & security → Microphone → Enable access for desktop apps.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Wake never triggers | Install vosk & model, check mic volume, lower `WAKE_WORD_THRESHOLD`, speak clearly |
| False activations | Increase `WAKE_WORD_THRESHOLD`, increase `WAKE_WORD_COOLDOWN_MS` |
| TTS triggers itself | Fixed: detection paused during `SPEAKING` + cooldown; if echo still, increase cooldown to 1000 |
| `vosk not installed` | `pip install vosk` — dummy fallback still works but less accurate |
| `sounddevice` fail | python.org Python, not Store; check Device Manager |

---

## Project Structure

```
nova/
├── app/
│   ├── __init__.py
│   ├── main.py              # State machine, hands-free loop, manual fallback
│   ├── config.py            # Whisper + TTS + Wake-word .env
│   ├── speech/
│   │   └── transcriber.py
│   ├── tts/
│   │   └── speaker.py
│   └── wakeword/            # NEW Phase 3
│       ├── __init__.py
│       └── detector.py      # WakeWordDetector (vosk/dummy), pause/resume, mic ownership
├── tests/__init__.py
├── .env.example
├── requirements.txt
└── README.md
```

---

## Privacy

- Wake detection local (Vosk/dummy), Whisper only after wake, TTS local.
- Audio in RAM only, released after transcribe. No recordings saved. No cloud. Logs don't contain speech.

---

## Roadmap

- [x] Phase 1 — STT
- [x] Phase 2 — TTS
- [x] Phase 3 — Hands-free wake word (current)
- [ ] Phase 4 — LLM agent, PC control

## License

MIT
