# Web UI Design: Gradio Interview Interface

**Date:** 2026-04-05
**Status:** Draft
**Scope:** Candidate-facing interview UI (v1); admin interface deferred

## Context

The assessment bot currently runs as a terminal CLI (`main.py`). This spec adds a web UI using Gradio so candidates can take interviews in a browser. The existing `src/` codebase remains unchanged — the web app is a thin presentation layer.

## Approach

**Thin wrapper (Approach A).** A single `web.py` module imports the existing `InterviewOrchestrator`, `InterviewBot`, and `load_questions` directly. No new abstractions or service layer. Common setup logic shared with `main.py` via a small `src/config.py` module.

## Architecture

```
web.py                ← Gradio app (new)
main.py               ← CLI entry point (minor refactor to use config)
src/
  config.py           ← shared setup: env, LLM init, question loading (new)
  orchestrator.py     ← unchanged
  modules.py          ← unchanged
  schema.py           ← unchanged
  data.py             ← unchanged
```

No modifications to `src/` business logic. `src/config.py` is pure extraction — three functions, ~30 lines.

## Shared Config (`src/config.py`)

Extracts duplicated setup from `main.py`:

1. **`load_config()`** — Reads `.env`, validates `OPENAI_API_KEY`, returns config dict (model, base URL).
2. **`init_llm(config)`** — Creates the DSPy LLM instance.
3. **`load_interview_questions(path)`** — Wraps `data.load_questions()` with default path.

`main.py` refactored to call these functions. No behavior change.

## UI Layout

Left sidebar (30%) + right chat panel (70%), built with Gradio Blocks:

```
┌─────────────────────────────────────────────────────┐
│  Assessment Bot                                     │
├──────────────┬──────────────────────────────────────┤
│  Progress    │  Chat area                           │
│              │                                      │
│  Topic:      │   Bot: Tell me about TCP...          │
│  Networking  │                                      │
│              │   You: TCP is a reliable...           │
│  Question:   │                                      │
│  3 / 12      │   Bot: Good explanation...            │
│              │                                      │
│  Attempts:   │                                      │
│  1 / 2       │  ┌──────────────────────────────┐    │
│              │  │ Type your answer...           │    │
│  ──────────  │  └──────────────────────────────┘    │
│  History     │                                      │
│  ✓ Q1: OSI   │                                      │
│  ✓ Q2: DNS   │                                      │
│  ○ Q3: TCP   │                                      │
│  · Q4: HTTP  │                                      │
└──────────────┴──────────────────────────────────────┘
```

**Left sidebar (30%):** Progress info, rebuilt after each turn:
- Current topic name
- Question number (X / Y)
- Attempt counter (X of 2)
- History list with evaluation badges (✓ correct, ✗ skipped, ~ ambiguous)

**Right panel (70%):** `gr.Chatbot` with streaming. Candidate input via textbox with submit. Chat history accumulates for the full session.

## Session Lifecycle

**Startup (once):**
1. `web.py` loads env/config/questions at module level
2. LLM initialized once (shared across sessions — DSPy bot is stateless)
3. Gradio app launches

**Per candidate session:**
1. Candidate lands → sees user ID form (chat panel and sidebar hidden)
2. On submit → user ID form disappears, chat panel + sidebar appear. New `InterviewOrchestrator` created, stored in `gr.State()` with session metadata (user ID, session UUID)
3. First question rendered as bot message, sidebar populated with initial progress
4. Interview loop runs via turn handler callback
5. When all questions done → summary message in chat, input textbox disabled

**Concurrent sessions:** Gradio handles natively. Each browser session gets independent `gr.State()` with its own orchestrator. No shared mutable state between sessions.

**No persistence.** If candidate closes the tab, session is lost. Server-side in-memory only. Database persistence can be added later without changing the UI layer.

**No authentication.** Anonymous access via user ID (matches current CLI). Auth to be added later.

## Turn Handler

Core callback triggered on each candidate submission:

```
candidate submits answer
  → get orchestrator + bot from gr.State()
  → build context (question, history, attempt #, last evaluation)
  → call bot() with retry logic (max 2 retries)
  → orchestrator.record_turn(command, evaluation)
  → if should_force_skip(): generate skip prompt
  → stream response tokens to chat (generator yielding tokens)
  → rebuild sidebar from orchestrator state
  → if interview complete: show summary, disable input
```

**Retry logic:** Matches `main.py` exactly — if LLM call fails, retry up to 2 times. If all retries fail, show error in chat, let candidate try again.

**Streaming:** Callback is a generator. Each `yield` appends to the chat message. Sidebar updates once after full response.

**Interview complete:** When `orchestrator.get_current_question()` returns `None`, yield summary message and disable input.

## Out of Scope (Deferred)

- Admin interface for monitoring/reviewing sessions
- Authentication and session persistence
- Resume across browser sessions
- Multi-language UI
- Custom theming beyond Gradio defaults
