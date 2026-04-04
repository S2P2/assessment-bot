from src.orchestrator import InterviewOrchestrator


def test_orchestrator_progression():
    questions = [{"id": "q1", "text": "Q1"}, {"id": "q2", "text": "Q2"}]
    orc = InterviewOrchestrator(questions)
    assert orc.get_current_question()["id"] == "q1"
    orc.record_turn("NEXT_QUESTION", "correct")
    assert orc.get_current_question()["id"] == "q2"
    assert orc.attempts == 0


def test_orchestrator_attempts():
    questions = [{"id": "q1", "text": "Q1"}]
    orc = InterviewOrchestrator(questions, max_attempts=2)
    orc.record_turn("GIVE_HINT", "incorrect")
    assert orc.attempts == 1
    assert orc.should_force_skip() is False
    orc.record_turn("GIVE_HINT", "incorrect")
    assert orc.attempts == 2
    assert orc.should_force_skip() is True


def test_orchestrator_clarify():
    questions = [{"id": "q1", "topic_name": "T1"}]
    orc = InterviewOrchestrator(questions)
    orc.record_turn("CLARIFY", "ambiguous")
    assert orc.attempts == 0  # Should NOT increment
    assert orc.current_idx == 0  # Should NOT move on


def test_orchestrator_get_next_topic_name():
    questions = [
        {"id": "q1", "text": "Q1", "topic_name": "Topic 1"},
        {"id": "q2", "text": "Q2", "topic_name": "Topic 2"},
    ]
    orc = InterviewOrchestrator(questions)

    # At index 0, next should be Topic 2
    assert orc.get_next_topic_name() == "Topic 2"

    # Move to index 1, next should be None
    orc.record_turn("NEXT_QUESTION", "correct")
    assert orc.get_next_topic_name() is None


def test_orchestrator_record_turn():
    questions = [{"id": "q1", "text": "Q1", "topic_name": "T1"}]
    orc = InterviewOrchestrator(questions)

    # First turn: Clarify
    orc.record_turn("CLARIFY", "ambiguous")
    assert orc.turns_in_question == 1
    assert orc.clarifications_requested == 1
    assert orc.last_evaluation == "ambiguous"

    # Second turn: Hint
    orc.record_turn("GIVE_HINT", "incorrect")
    assert orc.turns_in_question == 2
    assert orc.hints_given == 1
    assert orc.attempts == 1

    # Third turn: Next Question
    orc.record_turn("NEXT_QUESTION", "correct")
    assert len(orc.question_summaries) == 1
    assert orc.question_summaries[0]["final_evaluation"] == "correct"
    assert orc.turns_in_question == 0  # Reset


def test_orchestrator_empty_questions():
    orc = InterviewOrchestrator([])
    assert orc.get_current_question() is None


def test_orchestrator_unknown_command():
    questions = [{"id": "q1", "text": "Q1", "topic_name": "T1"}]
    orc = InterviewOrchestrator(questions)
    orc.record_turn("UNKNOWN", "correct")
    assert orc.turns_in_question == 1
    assert orc.attempts == 0
    assert orc.current_idx == 0


def test_should_force_skip_boundary():
    questions = [{"id": "q1", "text": "Q1"}]
    orc = InterviewOrchestrator(questions, max_attempts=2)

    orc.record_turn("GIVE_HINT", "incorrect")
    assert orc.should_force_skip() is False  # 1 < 2

    orc.record_turn("GIVE_HINT", "incorrect")
    assert orc.should_force_skip() is True  # 2 >= 2

    orc.record_turn("GIVE_HINT", "incorrect")
    assert orc.should_force_skip() is True  # 3 >= 2, stays True


def test_get_next_topic_name_single_question():
    questions = [{"id": "q1", "text": "Q1", "topic_name": "Only Topic"}]
    orc = InterviewOrchestrator(questions)
    assert orc.get_next_topic_name() is None
