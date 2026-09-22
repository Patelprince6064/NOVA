# Nova

Hands-free PC voice assistant (Windows).

## Current Phase

**Phase 1 — Voice Input + Speech-to-Text**

This phase provides a reliable local voice-input pipeline:

```
Microphone → Record speech → Speech-to-text → Display recognized text
```

No cloud services, no AI agent, no automation — just accurate local transcription.

---

## Features (Phase 1)

- Microphone detection (lists all input devices, auto-selects default)
- Push-to-talk voice recording (16 kHz, mono, float32)
- Local speech-to-text via `faster-whisper`
- Configurable Whisper model (`tiny` / `base` / `small` / ...)
- Handles silence, empty speech, and microphone errors gracefully
- Privacy-focused: audio stays in memory, never written to disk or sent externally
- Lightweight logging (no audio or sensitive speech content logged)

---

## Requirements

- Python 3.11+
- Windows 10/11
- A working microphone
- Internet connection on first run (to download the Whisper model)

---

## Installation

```powershell
# 1. Clone or create the project folder
cd nova

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate it (Windows PowerShell)
.venv\Scripts\Activate.ps1

# If activation is blocked, run once as Administrator:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Alternative — Command Prompt:
# .venv\Scripts\activate.bat

# 4. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Configuration

Copy the example env file and edit as needed:

```powershell
copy .env.example .env
notepad .env
```

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `base` | Model size: `tiny`, `base`, `small`, `medium`, `large-v3` |
| `WHISPER_DEVICE` | `cpu` | `cpu` or `cuda` |
| `WHISPER_COMPUTE_TYPE` | `int8` | `int8` (CPU), `float16` (CUDA) |
| `SAMPLE_RATE` | `16000` | Audio sample rate (Hz) |
| `MAX_RECORDING_SECONDS` | `15` | Auto-stop after this many seconds |
| `WHISPER_LANGUAGE` | _(auto)_ | Force language e.g. `en` |

Smaller models (`tiny`, `base`) are faster and use less RAM; larger models are more accurate.

---

## Usage

```powershell
# From the nova/ folder with venv activated:
python -m app.main
```

### What you will see

```
================================
        NOVA VOICE ENGINE
================================

Microphone: Default Microphone
Model: base
Sample Rate: 16000 Hz

Status: READY

Press ENTER to speak.
Press Q + ENTER to quit.
```

### Recording

1. Press **ENTER** to start recording.
2. Speak clearly.
3. Press **ENTER** again to stop (or wait for the 15s auto-stop).
4. Wait for transcription:

```
📝 You said:

"Open Brave and search YouTube"

Status: READY
```

5. Repeat or press **Q + ENTER** to quit.

---

## Microphone Permissions (Windows)

If you see `Microphone permission denied`:

1. Open **Settings → Privacy & security → Microphone**
2. Enable **Microphone access**
3. Enable **Let apps access your microphone**
4. Enable **Let desktop apps access your microphone** (for Python)
5. Restart Nova

If no microphone is shown:

```
ERROR: No microphone detected.
Please connect a microphone and restart Nova.
```

Check Device Manager → Audio inputs and outputs, and ensure your mic is not disabled.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `sounddevice` install fails | Install Python from python.org (not Windows Store) |
| Model download slow | First run downloads ~150 MB for `base`; use `tiny` for faster download |
| `WHISPER_DEVICE=cuda` fails | Install CUDA toolkit + cuDNN, or use `cpu` |
| Poor accuracy | Try `WHISPER_MODEL=small`, speak closer to mic, reduce background noise |
| `No speech detected` | Check mic volume in Windows Sound settings, speak louder |

---

## Project Structure

```
nova/
├── app/
│   ├── __init__.py
│   ├── main.py              # Entry point, mic detection, recording loop
│   ├── config.py            # .env configuration
│   └── speech/
│       ├── __init__.py
│       └── transcriber.py   # faster-whisper wrapper (model loaded once)
├── tests/
│   └── __init__.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Privacy

- Audio is kept in RAM only for transcription and released immediately after.
- No recordings are written to disk.
- No audio is sent to external services — transcription is fully local via `faster-whisper`.
- Logs do not contain speech content.

---

## Roadmap

- [x] **Phase 1** — Voice input + speech-to-text (current)
- [ ] Phase 2 — Wake word, agent, PC control
- [ ] Phase 3 — Browser automation, natural language understanding

---

## License

MIT (or your preferred license).
