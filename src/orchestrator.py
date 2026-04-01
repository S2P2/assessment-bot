class InterviewOrchestrator:
    def __init__(self, questions, max_attempts=2):
        self.questions = questions
        self.current_idx = 0
        self.attempts = 0
        self.max_attempts = max_attempts
        self.history = []

    def get_current_question(self):
        if self.current_idx >= len(self.questions):
            return None
        return self.questions[self.current_idx]

    def handle_command(self, command):
        if command in ["NEXT_QUESTION", "PROMPT_SKIP"]:
            self.current_idx += 1
            self.attempts = 0
        elif command == "GIVE_HINT":
            self.attempts += 1
        # CLARIFY does nothing to state (keeps same question, same attempts)

    def should_force_skip(self):
        return self.attempts >= self.max_attempts

    def get_next_topic_name(self):
        next_idx = self.current_idx + 1
        if next_idx >= len(self.questions):
            return None
        return self.questions[next_idx]["topic_name"]
