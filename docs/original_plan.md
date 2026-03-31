# Design Spec: IT Skill Interview Chatbot POC

## 1. Overview
A terminal-based LLM chatbot designed to interview IT staff on specific technical skills (e.g., SQL). The system uses a predefined question pool and follows a hybrid "agentic" flow: structured enough to cover all topics, but flexible enough for the LLM to provide hints, evaluate answers, and offer skips if the candidate is struggling.

## 2. Goals & Success Criteria
- **Iterative Interviewing**: Conducts a natural conversation, asking one question at a time.
- **Supportive Evaluation**: Provides up to 2 hints per question if the candidate is stuck.
- **Topic Coverage**: Ensures all topics in the question pool are visited.
- **Session Reporting**: Captures the full conversation and evaluation for post-interview analysis.

## 3. Architecture & Data Flow
The system uses a **Hybrid Orchestrator** model:
1. **Python Orchestrator**: Manages the "Rigid" state (current topic, question index, hint count).
2. **LLM Agent**: Manages the "Flexible" dialogue (evaluating answers, generating hints, deciding when to prompt for a skip).

### Data Flow
1. **Load Pool**: Load `questions.json`.
2. **Initialize State**: Start at Topic 1, Question 1.
3. **Turn Loop**:
   - **Evaluate/Respond**: LLM receives the question, criteria, and user input.
   - **Structured Output**: LLM returns a JSON object with:
     - `evaluation`: (Passed/Hint/Stuck)
     - `thought`: Internal reasoning for the decision.
     - `response`: The text shown to the user.
     - `command`: Instruction to the Orchestrator (`NEXT_QUESTION`, `GIVE_HINT`, `PROMPT_SKIP`).
   - **Update State**: Orchestrator updates the pointer based on the `command`.
4. **Finalize**: When all topics are exhausted, save history to a report file.

## 4. Components

### 4.1 Data Schema (`questions.json`)
```json
{
  "interview_id": "string",
  "topics": [
    {
      "topic_name": "string",
      "questions": [
        {
          "id": "string",
          "text": "string",
          "criteria": "string",
          "hints": ["string", "string"]
        }
      ]
    }
  ]
}
```

### 4.2 Interview Orchestrator (`orchestrator.py`)
- **State**: `current_topic_idx`, `current_question_idx`, `hints_used`.
- **Logic**: 
  - `get_next_payload()`: Combines the current question data with context for the LLM.
  - `handle_command(command)`: Logic for advancing indices or resetting hints.

### 4.3 LLM Client (`llm_client.py`)
- **System Prompt**: Defines the persona (interviewer), the evaluation rules, and the "hybrid skip" logic.
- **Response Parsing**: Ensures the LLM output is valid JSON and maps it to the internal state.

### 4.4 Report Generator (`report.py`)
- Formats the conversation history into a markdown report.

## 5. Error Handling & Edge Cases
- **Invalid LLM Output**: Fallback to a "retry" or a safe default (e.g., asking the question again).
- **Abrupt Exit**: Ensure the current progress is saved if the user terminates the CLI.
- **Ambiguous Answers**: The LLM is instructed to ask for clarification if the answer is partially correct but missing key criteria.

## 6. Testing Strategy
- **Mock Question Pool**: Test with a small JSON file (2 topics, 1 question each).
- **Automated Validation**: Run the Orchestrator logic without the LLM (using mock responses) to verify state transitions.
- **Manual "Stress" Test**: Attempt to confuse the LLM with off-topic answers to ensure it stays on track.