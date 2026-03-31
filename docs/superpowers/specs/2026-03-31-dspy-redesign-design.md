# Design Spec: DSPy Interview Bot POC

## 1. Overview
A terminal-based IT skill interview chatbot redesigned using the **DSPy framework**. The system uses a **Unified Predictor** model to evaluate answers and generate responses in a single LLM call, while a Python **Orchestrator** manages the rigid state (question order, attempt limits).

## 2. Goals & Success Criteria
- **Unified Logic**: Replace multi-step prompt chains with a single `dspy.TypedPredictor`.
- **Guideline-Driven Hints**: Use natural language strategies instead of fixed hint strings.
- **Rigid Progression**: Maintain strict question-by-question flow for the initial POC.
- **Traceability**: Capture LLM reasoning for every evaluation.

## 3. Architecture & Data Flow

### 3.1 Components
1. **Data Layer**: Flat `questions.json` with `hint_guidelines`.
2. **DSPy Layer**: 
   - `InterviewAction` (Pydantic Model): Structured output schema.
   - `InterviewTurn` (Signature): Maps context + input to action.
   - `Module`: Wraps `dspy.TypedPredictor(InterviewTurn)`.
3. **Orchestrator Layer**: Python loop managing `current_topic`, `question_index`, and `attempts`.

### 3.2 Data Flow
1. **Fetch**: Orchestrator gets the current question data.
2. **Predict**: DSPy module processes `user_input` + `history` + `criteria`.
3. **Logic**: 
   - If `action.evaluation` == "correct" -> `command` = `NEXT_QUESTION`.
   - If `action.evaluation` == "incorrect" AND `attempts < max` -> `command` = `GIVE_HINT`.
   - If `attempts >= max` -> Orchestrator overrides to `PROMPT_SKIP`.
4. **Update**: Orchestrator moves indices and resets counters.

## 4. Implementation Details

### 4.1 Input Schema (`questions.json`)
```json
{
  "topic": "string",
  "questions": [
    {
      "id": "string",
      "text": "string",
      "criteria": "string",
      "hint_guidelines": "string"
    }
  ]
}
```

### 4.2 DSPy Module
```python
class InterviewBot(dspy.Module):
    def __init__(self):
        super().__init__()
        self.predictor = dspy.TypedPredictor(InterviewTurn)

    def forward(self, **kwargs):
        return self.predictor(**kwargs)
```

## 5. Potential Improvements (Post-POC)
- **Momentum Awareness**: Use LLM-detected sentiment to allow extra attempts.
- **Cross-Topic Memory**: Inject performance summaries from previous topics.
- **Optimization**: Use `dspy.BootstrapFewShot` to tune the prompt based on "Gold" interview transcripts.

## 6. Testing Strategy
- **Unit Tests**: Verify Pydantic validation on the `InterviewAction` model.
- **Integration**: Run with a mock question pool to verify Orchestrator state transitions.
- **Trace Audit**: Review the `reasoning` field to ensure evaluation matches `criteria`.
