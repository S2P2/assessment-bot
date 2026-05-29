# Handoff: Assessment Bot — Optimization Pipeline Implementation

**Date:** 2026-05-29
**Branch:** main (40aaf34)
**Purpose:** Implement the InterviewBot optimization pipeline (POC)

## Context

Assessment Bot is at v0.6.0. It's a DSPy-based IT skill interview chatbot with CLI + Gradio web UI, session persistence, and end-of-interview reports. The next milestone is building a pipeline to optimize `InterviewBot`'s per-turn evaluation accuracy.

## Decisions Made (this session)

All design decisions are resolved. Read the ADR for optimizer choice rationale:

- **ADR:** `docs/adr/0001-bootstrap-few-shot-for-poc.md`
- **Domain glossary:** `CONTEXT.md` (no changes needed — new terms are general ML concepts, not domain-specific)

### Plan summary

1. **Training data collection script** — runs InterviewBot against pre-written answer variants per question
   - Variants hardcoded in a JSON file
   - Coverage: clearly correct, clearly incorrect, partially correct, edge case, vague/too short
   - ~5-7 variants per question → ~15-21 examples for 3 questions
   - Each example: full InterviewTurn inputs + `expected_evaluation` + `expected_command`
   - Script logs every LLM output alongside expected labels for review

2. **Metric** — evaluation-as-hard-gate
   - `evaluation` wrong → 0.0
   - `evaluation` correct + `command` correct → 1.0
   - `evaluation` correct + `command` wrong → 0.5

3. **Optimizer** — `BootstrapFewShot` (smoke test with ~20 examples)
   - Graduate to COPRO/MIPROv2 when question pool grows

4. **Deferred** (not POC blockers)
   - Question quality gate (automated criteria validation)
   - SummaryBot optimization
   - LLM-assisted answer variant generation

## Key source files

- `src/signatures.py` — `InterviewTurn` signature (the optimization target)
- `src/modules.py` — `InterviewBot` module
- `src/schema.py` — `InterviewAction` Pydantic model (evaluation, command, reasoning, response)
- `src/orchestrator.py` — `InterviewOrchestrator` state machine
- `src/config.py` — shared config, LM init
- `web.py` / `main.py` — entry points (reference for how bot is called)
- `questions.json` — 3 questions (sql-1, sql-2, python-1), validated against `schemas/questions.schema.json`

## What to implement

1. **Create answer variants file** — e.g. `training/answer_variants.json`
   - Structure: per-question array of `{user_input, expected_evaluation, expected_command, variant_type}`
   - Cover 5-7 variants per question (see plan summary above)

2. **Create data collection script** — e.g. `scripts/collect_training_data.py`
   - Loads questions from `questions.json`
   - For each question, runs InterviewBot with each variant's `user_input`
   - Logs: inputs, expected labels, actual LLM output
   - Outputs reviewable JSON/CSV

3. **Create metric function** — e.g. `src/metric.py`
   - Evaluation-as-hard-gate logic (see plan summary)

4. **Create optimization script** — e.g. `scripts/optimize.py`
   - Loads labeled data, runs `BootstrapFewShot`, saves compiled program

5. **Tests** for metric function

## Suggested skills

- **dspy-expert** — Read this FIRST. Covers DSPy 3.2.x optimizers (BootstrapFewShot), evaluation, and save/load. Located at `.agents/skills/dspy-expert/SKILL.md`.
- **tdd** — For building the metric function test-first.

## Notes

- The bot uses `dspy.ChainOfThought(InterviewTurn)` — the optimizer works on the underlying predictor
- `attempt_number`, `last_evaluation`, `history` fields need sensible defaults in training examples (first-turn scenarios: attempt=0, last_eval="None", history=[])
- The existing `run_mocked_interview.py` is a reference for how to call the bot outside the main loop
- Question validation gate is deferred — note any bad criteria discovered during data collection for future follow-up
