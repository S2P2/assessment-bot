# Gradio Web UI Known Issues

**Branch:** `feat/gradio-ui`
**Reported:** 2026-04-09 after first end-to-end testing

Core interview flow works start to finish. These are UX polish and session management fixes needed before merge.

## Bugs

### 1. Session file proliferation

Files named by UUID. Every server restart + page refresh creates new files for the same user. During testing, 19 files were created for just 3 users.

**Fix:** Name files by `user_id` (`sessions/{user_id}.json`). One file per user. Eliminates scanning, prevents duplicates, makes resume trivial. UUID stays inside the file for the registry key.

### 2. "..." empty bubble on first turn

An empty user message bubble appears when the interview starts, before the candidate has typed anything.

**Root cause:** `respond` callback is not split into user/bot chained pattern. Empty message may be submitted on group visibility change.

**Fix:** Chain `msg_input.submit(user_fn).then(bot_fn)`. Guard against empty messages in `user_fn`.

### 3. User answer delayed until LLM responds

After typing an answer and pressing Enter, the candidate's message doesn't appear in the chat until the full LLM response comes back.

**Root cause:** Single `respond` callback appends user message, calls LLM, then appends bot response — all in one return.

**Fix:** Same as #2. Split into chained callbacks: `user_fn` returns immediately (candidate sees their answer), `bot_fn` runs after LLM call.

### 4. No Send button on chat textbox

The chat input only responds to Enter key. No visible submit button.

**Root cause:** `submit_btn=True` was removed (not a Gradio 6 parameter) but no replacement was added.

**Fix:** Add `gr.Button("Send")` next to the textbox. Wire with `gr.on(triggers=[send_btn.click, msg_input.submit], ...)`.

### 5. Textbox not disabled when interview completes

When the interview ends, the textbox remains active. Submitting produces no response (correct behavior) but gives no visual feedback.

**Fix:** Return `gr.Textbox(interactive=False)` instead of `""` for `msg_input` when interview is complete.

## Display Preferences

### 6. Sidebar history items render on same line

Question history entries appear concatenated on a single line instead of stacked.

**Root cause:** `_build_history` uses `"\n".join(lines)` but Markdown treats single newlines as spaces.

**Fix:** Use markdown list format (`- ✓ sql-1`) with `"\n".join()` so each item renders on its own line.
