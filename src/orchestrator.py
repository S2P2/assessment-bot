class InterviewOrchestrator:
    def __init__(self, questions, max_attempts=2):
        self.questions = questions
        self.current_idx = 0
        self.attempts = 0  # Hint attempts (drives force-skip logic)
        self.max_attempts = max_attempts
        self.history = []

        # New State
        self.turns_in_question = 0
        self.hints_given = 0
        self.clarifications_requested = 0
        self.last_evaluation = "None"
        self.evaluation_history = []
        self.question_summaries = []

    def get_current_question(self):
        if self.current_idx >= len(self.questions):
            return None
        return self.questions[self.current_idx]

    def record_turn(self, command, evaluation):
        self.last_evaluation = evaluation
        self.evaluation_history.append(evaluation)
        self.turns_in_question += 1

        if command in ["NEXT_QUESTION", "PROMPT_SKIP"]:
            # Record summary before moving on
            q = self.get_current_question()
            summary = {
                "question_id": q.get("id"),
                "final_evaluation": evaluation,
                "total_turns": self.turns_in_question,
                "hints_used": self.hints_given,
                "clarifications_used": self.clarifications_requested,
                "was_force_skipped": command == "PROMPT_SKIP",
            }
            self.question_summaries.append(summary)

            self.current_idx += 1
            self.turns_in_question = 0
            self.hints_given = 0
            self.clarifications_requested = 0
            self.attempts = 0
            self.evaluation_history = []
        elif command == "GIVE_HINT":
            self.hints_given += 1
            self.attempts += 1  # maintain for should_force_skip
        elif command == "CLARIFY":
            self.clarifications_requested += 1

    def should_force_skip(self):
        return self.attempts >= self.max_attempts

    def get_next_topic_name(self):
        next_idx = self.current_idx + 1
        if next_idx >= len(self.questions):
            return None
        return self.questions[next_idx]["topic_name"]
