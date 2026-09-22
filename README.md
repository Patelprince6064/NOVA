# Nova

Hands-free PC voice assistant (Windows).

## Current Phase

**Phase 8 — Multi-Step Task Execution**

```
👂 "Hey Nova"
      ↓
🎤 Listening (no ENTER)
      ↓
📝 STT (faster-whisper)
      ↓
Fast router → Multi-step? → TaskPlanner (LLM or heuristic, JSON only)
                                        ↓
                                Validator (allowlist, max 8, no code/shell, no unsafe)
                                        ↓
                                TaskExecutor (sequential, verify, retry 1, timeout 60s, cancel)
                                        ↓
                ┌───────────────┼───────────────┐
                PC Tools    Browser Tools   Vision Tools
                        └───────┼───────┘
                                ↓
                            TTS
```

One task = 2-8 validated steps, each verified, single action per step, no autonomous code.

---

## Features

### Phase 1-2: STT + TTS
- `faster-whisper` 16kHz, `pyttsx3`

### Phase 3: Wake Word
- `vosk` `hey nova`, state machine, `--manual`

### Phase 4: PC Control
- Apps/websites, type, keys, hotkeys allowlisted, mouse

### Phase 5: Natural Language
- `CommandInterpreter` strict JSON, `validate_action`, fast path bypasses LLM

### Phase 6: Browser
- Playwright `BrowserController` reused, `open_url/search_web/youtube_search/back/forward/refresh/scroll/close`

### Phase 7: Vision
- `ScreenCapture` MSS, `ScreenAnalyzer` vision, `ScreenElement` with confidence, on-demand only

### Phase 8 — Multi-Step (new)
- **`app/agent/planner.py` `TaskPlanner`**: strict prompt (max 8 steps, only allowlisted tools, no code/shell, ask clarification if ambiguous, reject unsafe), LLM via `openai` (json_object) or heuristic fallback (splits on `and/,/then`, maps keywords, handles `open Brave, go to YouTube, search for X, play first result` → 5 steps)
- **`app/agent/schemas.py`**: `TaskPlan`/`TaskStep` (`id, action, parameters, expected_result, timeout`), `ALLOWED_AGENT_ACTIONS` (20 actions + wait)
- **`app/agent/validator.py`**: `validate_plan` checks allowed action, params valid (app alias, website, key, hotkey, scroll, query length), `MAX_TASK_STEPS` (8), dangerous patterns (`delete, password, bank, log into, gmail read, purchase` etc.), no `import/exec/eval/os.system/subprocess`, duplicate ids
- **`app/agent/executor.py` `TaskExecutor`**: states `IDLE/PLANNING/VALIDATING/RUNNING/PAUSED/FAILED/COMPLETED/CANCELLED`, executes step→verify (`open_application` foreground, `open_url` browser url, `youtube_search` results, `find/click` confidence), wait `MAX_WAIT_SECONDS` (10), retry `MAX_STEP_RETRIES` (1) with 1.5s wait, timeout `MAX_TASK_DURATION_SECONDS` (60), cancel via `cancel()` (`Stop/Cancel/Never mind`), progress terminal `NOVA TASK` with ✓/→, in-memory only
- **`wait` action**: `{"action":"wait","parameters":{"seconds":2}}` 1-10s, validated
- **Vision steps:** `find_screen_element`→`ScreenAnalyzer.find_element` confidence≥`VISION_MIN_CONFIDENCE` (0.70), `click_screen_element`→`pyautogui.moveTo+click` after find (direct, not via demo flag, verified), `analyze_screen`→description
- **Safety:** planner never produces `eval/exec/os.system`, validator rejects `code: page.click`, `unsafe` task (delete files, Chrome log into Gmail read emails…) rejected, `too many steps` >8 rejected `That task is too complex…`, simple `open Brave` still fast path not planner
- **Performance:** simple commands fast, multi-step only when `is_multi_step_request` (≥2 verbs + connector) true, planner reused, LLM only when needed

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

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `AGENT_ENABLED` | `true` | Enable multi-step planner |
| `MAX_TASK_STEPS` | `8` | 1-20 |
| `MAX_STEP_RETRIES` | `1` | 0-5 |
| `MAX_TASK_DURATION_SECONDS` | `60` | 10-300 |
| `MAX_WAIT_SECONDS` | `10` | 1-30 |
| `VISION_MIN_CONFIDENCE` | `0.70` |  |
| `VISION_CLICK_TEST_ENABLED` | `false` | Phase7 demo flag (Phase8 click_screen_element works regardless) |

Plus Phase 1-7 vars.

---

## Usage

Hands-free:
```powershell
python -m app.main
# 👂 Waiting for "hey nova"...
# Hey Nova → "open Brave and go to YouTube" → Task 2 steps → ✓ → Done.
# Hey Nova → "open Brave, go to YouTube, search for Arijit Singh, and play the first song" → 5 steps → find+click first video → Done.
# Hey Nova → "open Brave" → fast path (no planner) → Opening Brave.
# During task say "Stop" → Task cancelled.
```

Manual:
```powershell
python -m app.main --manual
```

One action per step, verified, not blind. `Stop`/`Cancel`/`Never mind` cancels.

---

## Project Structure

```
nova/
├── app/
│   ├── main.py                 # is_multi_step + planner routing, agent init
│   ├── config.py               # +AGENT
│   ├── speech/transcriber.py
│   ├── tts/speaker.py
│   ├── wakeword/detector.py
│   ├── pc/{controller,actions}
│   ├── ai/{interpreter,schemas,prompts}
│   ├── browser/{controller,actions,sites}
│   ├── vision/{screenshot,analyzer,schemas}
│   └── agent/                  # NEW Phase 8
│       ├── __init__.py
│       ├── planner.py          # TaskPlanner LLM+heuristic
│       ├── schemas.py          # TaskPlan/Step
│       ├── validator.py        # validate_plan safety
│       └── executor.py         # TaskExecutor sequential
├── .env.example
├── requirements.txt
└── README.md
```

---

## Privacy / Safety

- Task plans JSON only, validated before exec, no code/shell, no arbitrary file delete, no password/banking, no email, no purchases, no CAPTCHA, max 8 steps, timeout 60s, screenshots on demand only for vision steps, in-memory task state.

---

## Roadmap

- [x] Phase 1 STT
- [x] Phase 2 TTS
- [x] Phase 3 Wake Word
- [x] Phase 4 PC Control
- [x] Phase 5 Natural Language
- [x] Phase 6 Browser Control
- [x] Phase 7 Vision
- [x] Phase 8 Multi-Step (current)
- [ ] Phase 9 full autonomy

## License

MIT
