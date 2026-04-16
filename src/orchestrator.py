class InterviewOrchestrator:
    def __init__(self, questions, max_hints=2, max_ambiguous_turns=3):
        self.questions = questions
        self.current_idx = 0
        self.max_hints = max_hints
        self.max_ambiguous_turns = max_ambiguous_turns
        self.history = []

        # Turn tracking
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

    def record_turn(self, evaluation):
        self.last_evaluation = evaluation
        self.evaluation_history.append(evaluation)
        self.turns_in_question += 1

        if evaluation == "correct":
            self._advance_question(evaluation)
        elif evaluation in ("partially_correct", "incorrect"):
            self.hints_given += 1
            if self.hints_given >= self.max_hints:
                self._advance_question(evaluation, force_skip=True)
        elif evaluation == "ambiguous":
            self.clarifications_requested += 1
            if self.clarifications_requested >= self.max_ambiguous_turns:
                self._advance_question(evaluation, force_skip=True)

    def _advance_question(self, evaluation, force_skip=False):
        """Record summary and advance to the next question."""
        q = self.get_current_question()
        summary = {
            "question_id": q.get("id"),
            "final_evaluation": evaluation,
            "total_turns": self.turns_in_question,
            "hints_used": self.hints_given,
            "clarifications_used": self.clarifications_requested,
            "was_force_skipped": force_skip,
        }
        self.question_summaries.append(summary)
        self.current_idx += 1
        self.turns_in_question = 0
        self.hints_given = 0
        self.clarifications_requested = 0
        self.evaluation_history = []

    def get_next_topic_name(self):
        next_idx = self.current_idx + 1
        if next_idx >= len(self.questions):
            return None
        return self.questions[next_idx]["topic_name"]
