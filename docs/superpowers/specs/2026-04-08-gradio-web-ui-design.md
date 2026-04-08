# Gradio 6 Web UI Design

**Date:** 2026-04-08
**Status:** Approved
**Supersedes:** 2026-04-05-web-ui-design.md
**Scope:** Candidate-facing interview UI (v1); admin interface deferred

## Context

The assessment bot currently runs as a terminal CLI (`main.py`). This spec adds a web UI using Gradio 6 so candidates can take interviews in a browser. The existing `src/` business logic remains unchanged — the web app is a thin presentation layer with session persistence.

## Approach

**Thin wrapper with server-side session registry.** A single `web.py` module imports the existing `InterviewOrchestrator`, `InterviewBot`, and `load_questions` directly. Session data split into display-safe client state (`gr.State()`) and sensitive server-side registry. Common setup logic shared with `main.py` via `src/config.py`.

## Architecture

```
web.py                ← Gradio 6 app (new)
main.py               ← CLI entry point (minor refactor to use config)
src/
  config.py           ← shared setup: env, LLM init, question loading (new, ~30 lines)
  session.py          ← JSON session save/load/resume + server-side registry (new, ~60 lines)
  orchestrator.py     ← unchanged
  modules.py          ← unchanged
  signatures.py       ← unchanged
  schema.py           ← unchanged
  data.py             ← unchanged
sessions/             ← JSON session files (gitignored)
```

No modifications to `src/` business logic. `src/config.py` is pure extraction from `main.py`. `src/session.py` is new but doesn't touch existing code.

## Shared Config (`src/config.py`)

Extracts duplicated setup from `main.py`. Three functions, ~30 lines:

1. **`load_config()`** — Reads `.env`, validates `OPENAI_API_KEY`, returns config dict (model, base_url, api_key).
2. **`init_lm(config)`** — Creates and configures the DSPy LM instance.
3. **`load_interview_data(path)`** — Wraps `data.load_questions()` + `flatten_questions()` with default path. Returns (raw data, flat questions).

`main.py` refactored to call these functions. No behavior change.

## Security: Server-Side Session Registry

`gr.State()` sends data to the client browser as JSON. If full question objects (including `criteria`, `hint_guidelines`) were stored in Gradio state, candidates could inspect browser dev tools and see evaluation rubrics, hint guidelines, and all future questions.

**Mitigation:** Split session data into display-safe client state and sensitive server-side state.

**Server-side session registry (`src/session.py`):**
- Module-level dict mapping session UUID → `SessionData` (orchestrator, questions, metadata)
- Contains all sensitive data — never sent to the browser
- Looked up by UUID on each callback

**Client-side `gr.State()` contents (display-safe only):**
```python
{
    "session_uuid": str,    # lookup key for server-side data
    "user_id": str,         # for display
}
```

No criteria, no hint guidelines, no future question text, no evaluation details in client state.

## UI Layout

Using Gradio 6's `gr.Sidebar()` + `gr.Blocks()`:

```
┌─────────────────────────────────────────────────────────┐
│  Assessment Bot                              [sidebar ▼] │
├──────────────┬──────────────────────────────────────────┤
│  Progress    │  Interview                                │
│              │                                          │
│  Topic:      │  Bot: Tell me about TCP handshakes...    │
│  Networking  │                                          │
│              │  You: TCP uses a three-way handshake...   │
│  Question:   │                                          │
│  3 / 12      │  Bot: Good explanation of SYN/SYN-ACK... │
│              │                                          │
│  Attempts:   │                                          │
│  1 / 2       │  ┌────────────────────────────────────┐  │
│              │  │ Type your answer...          [Send] │  │
│  ──────────  │  └────────────────────────────────────┘  │
│  History     │                                          │
│  ✓ Q1: OSI   │                                          │
│  ✓ Q2: DNS   │                                          │
│  ○ Q3: TCP   │                                          │
│  · Q4: HTTP  │                                          │
└──────────────┴──────────────────────────────────────────┘
```

**Two UI states:**

1. **Pre-interview:** Sidebar hidden. Center shows user ID text field + "Start Interview" button. No chat visible.
2. **During/after interview:** User ID form replaced by sidebar + chat. Sidebar rebuilt after each turn from orchestrator state. Chat uses `gr.Chatbot` with message history. Input textbox disabled when interview completes.

**Sidebar contents (rebuilt after each turn):**
- Current topic name
- Question progress (X / Y)
- Attempt counter (X of 2)
- History list with evaluation badges (✓ correct, ✗ skipped, ~ ambiguous)
- "Resume Session" button if a saved session exists for the entered user ID

**No streaming.** Full bot response appears after LLM call completes. A "Thinking..." placeholder shown while waiting.

**Gradio 6 specifics:**
- `gr.Sidebar()` for collapsible progress panel
- Theme/CSS passed to `demo.launch()`, not `gr.Blocks()`
- `api_visibility="private"` on all event handlers
- Chat messages in `{"role": "user", "content": "..."}` format

## Session Lifecycle

**Startup (once, at module level):**
1. `web.py` loads env/config/questions via `src/config.py`
2. LLM initialized once (shared across sessions — DSPy bot is stateless)
3. Server-side session registry created as module-level dict
4. Gradio app launches

**Per-candidate flow:**

1. Candidate opens UI → sees user ID form (sidebar + chat hidden)
2. Candidate enters user ID + submits:
   - `session.py` checks `sessions/` for existing session with this user ID
   - If found: resume — load orchestrator state from JSON, populate registry
   - If not found: new session — create fresh orchestrator, save to `sessions/`
   - Chat + sidebar appear, first question shown
3. Each turn:
   - Callback receives session UUID from `gr.State()` (client-side)
   - Looks up full orchestrator + questions from server-side registry
   - Calls bot, records turn
   - Saves updated state to `sessions/<uuid>.json`
   - Returns: response text to chat, display-safe progress to sidebar
4. Interview complete:
   - Summary message in chat
   - Input disabled
   - Final session file saved

**Concurrent sessions:** Gradio handles natively. Each browser session gets independent `gr.State()` with its own UUID. Server-side registry maps each UUID to isolated orchestrator + question data.

## Session Persistence (`src/session.py`)

**API:**
- `create_session(user_id, questions, interview_id) -> str` — new session, returns UUID
- `resume_session(user_id, questions) -> str | None` — load from JSON if exists, returns UUID
- `get_session(uuid) -> SessionData` — callback lookup
- `save_session(uuid)` — persist current state to disk
- `remove_session(uuid)` — cleanup

**Session file format (`sessions/<uuid>.json`):**
```json
{
  "uuid": "...",
  "user_id": "...",
  "created_at": "2026-04-08T...",
  "updated_at": "2026-04-08T...",
  "interview_id": "...",
  "orchestrator": {
    "current_idx": 2,
    "attempts": 1,
    "turns_in_question": 0,
    "hints_given": 0,
    "clarifications_requested": 0,
    "last_evaluation": "correct",
    "history": ["User: ...", "Interviewer: ..."],
    "evaluation_history": ["..."],
    "question_summaries": ["..."]
  }
}
```

Question text, criteria, and hint guidelines are NOT in the session file. They're loaded from `questions.json` at resume time.

## Turn Handler

Core callback triggered on each candidate submission:

```
candidate submits answer
  → get session_uuid from gr.State()
  → look up SessionData from server-side registry
  → get current question from orchestrator
  → if interview complete: show summary, disable input, return
  → show "Thinking..." placeholder in chat
  → call bot with retry (max 2 retries, same as main.py)
  → orchestrator.record_turn(command, evaluation)
  → apply force-skip override if needed
  → save session to disk
  → rebuild sidebar from orchestrator state (display-safe only)
  → if complete: show summary, disable input
```

**Retry logic:** Identical to `main.py:_call_bot_with_retry`. Two retries, then error message in chat. No session state mutation on failure.

**MLflow integration:** Same span/trace pattern as `main.py` — wrapped around the bot call with question metadata.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| LLM call fails (all retries) | Error message in chat. Candidate can retry answer. Session state unchanged. |
| Session UUID not in registry | Error shown, redirect to user ID form. Candidate can resume from disk. |
| Corrupted session file | Error with session UUID for debugging. Fresh session option offered. |
| Missing `OPENAI_API_KEY` | App fails to launch. Caught at startup. |

## Testing

| What | How |
|------|-----|
| `src/config.py` | Unit tests for env parsing, missing key error |
| `src/session.py` | Unit tests for create/resume/save, corrupted file, missing session |
| `web.py` turn handler | Integration tests with mocked bot — orchestrator updates, sidebar data, error cases |
| `web.py` session resume | Integration test — save, reload, verify state matches |
| Security | Test that `gr.State()` output contains no criteria/hints beyond displayed data |
| Existing tests | Must continue to pass unchanged |

Tests in `tests/` mirroring package structure: `test_config.py`, `test_session.py`, `test_web.py`.

## Dependencies

Only `gradio>=6.0` added to `pyproject.toml`. No other new dependencies.

## File Changes Summary

| File | Action |
|------|--------|
| `web.py` | New — Gradio app |
| `src/config.py` | New — shared setup (~30 lines) |
| `src/session.py` | New — session persistence + registry (~60 lines) |
| `main.py` | Minor refactor — use `config.py` |
| `pyproject.toml` | Add `gradio>=6.0` |
| `.gitignore` | Add `sessions/` |
| `tests/test_config.py` | New |
| `tests/test_session.py` | New |
| `tests/test_web.py` | New |

## Out of Scope (Deferred)

- Admin interface for monitoring/reviewing sessions
- Authentication
- Streaming responses (can be added later without changing the UI layer)
- Dockerfile (local dev for now, can be added later)
- Custom theming beyond Gradio defaults
- Multi-language UI
