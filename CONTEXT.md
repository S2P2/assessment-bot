# Assessment Bot

An IT skill interview chatbot that evaluates candidates through structured technical questions, providing hints and tracking performance across topics.

## Language

**Interview**:
A structured conversation covering all topics in a question pool, from start to final report.
_Avoid_: Session, assessment, test

**Topic**:
A subject area (e.g. "SQL Basics") containing one or more questions.
_Avoid_: Category, section, module

**Question**:
A single technical prompt with evaluation criteria and hint guidelines.
_Avoid_: Prompt, item, problem

**Turn**:
One exchange: the candidate's answer plus the interviewer's evaluation and response.
_Avoid_: Exchange, round, interaction

**Evaluation**:
The LLM's judgment of a candidate's answer: correct, incorrect, or ambiguous.
_Avoid_: Score, grade, rating

**Command**:
The LLM's instruction to the orchestrator for what happens next: NEXT_QUESTION, GIVE_HINT, PROMPT_SKIP, or CLARIFY.
_Avoid_: Action, directive

**Report**:
The end-of-interview artifact containing per-question breakdown, aggregate score, and improvement summary.
_Avoid_: Summary, results, feedback

**Improvement Summary**:
An LLM-generated synthesis of the candidate's strengths and weaknesses, organized by topic with an overall verdict.
_Avoid_: Feedback, review, analysis

**Session**:
A persisted interview state (history, position, summaries) keyed by user ID. Enables resuming interrupted interviews.
_Avoid_: Interview, state, context

**Candidate**:
The person being interviewed.
_Avoid_: User, interviewee, applicant

## Flagged ambiguities

- "Session" vs "Interview": A **session** is the persisted state; an **interview** is the full conversation. One interview maps to one session.
- "Evaluation" vs "Score": **Evaluation** is per-turn (correct/incorrect/ambiguous). The **score** is the aggregate raw count at the end.
