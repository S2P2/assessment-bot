from src.orchestrator import InterviewOrchestrator


def test_orchestrator_correct_advances():
    questions = [{"id": "q1", "text": "Q1"}, {"id": "q2", "text": "Q2"}]
    orc = InterviewOrchestrator(questions)
    assert orc.get_current_question()["id"] == "q1"
    orc.record_turn("correct")
    assert orc.get_current_question()["id"] == "q2"
    assert orc.hints_given == 0


def test_orchestrator_incorrect_increments_hints():
    questions = [{"id": "q1", "text": "Q1"}]
    orc = InterviewOrchestrator(questions, max_hints=2)
    orc.record_turn("incorrect")
    assert orc.hints_given == 1
    assert orc.current_idx == 0


def test_orchestrator_partially_correct_increments_hints():
    questions = [{"id": "q1", "text": "Q1"}]
    orc = InterviewOrchestrator(questions, max_hints=2)
    orc.record_turn("partially_correct")
    assert orc.hints_given == 1
    assert orc.current_idx == 0


def test_orchestrator_ambiguous_no_penalty():
    questions = [{"id": "q1", "topic_name": "T1"}]
    orc = InterviewOrchestrator(questions)
    orc.record_turn("ambiguous")
    assert orc.hints_given == 0
    assert orc.current_idx == 0
    assert orc.clarifications_requested == 1


def test_orchestrator_force_skip_on_incorrect():
    questions = [{"id": "q1", "text": "Q1"}]
    orc = InterviewOrchestrator(questions, max_hints=2)
    orc.record_turn("incorrect")
    assert orc.current_idx == 0
    orc.record_turn("incorrect")
    assert orc.current_idx == 1
    assert orc.question_summaries[0]["was_force_skipped"] is True


def test_orchestrator_force_skip_on_partially_correct():
    questions = [
        {"id": "q1", "text": "Q1", "topic_name": "T1"},
        {"id": "q2", "text": "Q2"},
    ]
    orc = InterviewOrchestrator(questions, max_hints=2)
    orc.record_turn("partially_correct")
    orc.record_turn("partially_correct")
    assert orc.current_idx == 1
    assert orc.question_summaries[0]["was_force_skipped"] is True


def test_orchestrator_get_next_topic_name():
    questions = [
        {"id": "q1", "text": "Q1", "topic_name": "Topic 1"},
        {"id": "q2", "text": "Q2", "topic_name": "Topic 2"},
    ]
    orc = InterviewOrchestrator(questions)
    assert orc.get_next_topic_name() == "Topic 2"
    orc.record_turn("correct")
    assert orc.get_next_topic_name() is None


def test_orchestrator_record_turn_tracks_state():
    questions = [{"id": "q1", "text": "Q1", "topic_name": "T1"}]
    orc = InterviewOrchestrator(questions)

    # First turn: ambiguous (clarify)
    orc.record_turn("ambiguous")
    assert orc.turns_in_question == 1
    assert orc.clarifications_requested == 1
    assert orc.last_evaluation == "ambiguous"

    # Second turn: incorrect (hint)
    orc.record_turn("incorrect")
    assert orc.turns_in_question == 2
    assert orc.hints_given == 1

    # Third turn: correct (advance)
    orc.record_turn("correct")
    assert len(orc.question_summaries) == 1
    assert orc.question_summaries[0]["final_evaluation"] == "correct"
    assert orc.turns_in_question == 0  # Reset


def test_orchestrator_empty_questions():
    orc = InterviewOrchestrator([])
    assert orc.get_current_question() is None


def test_orchestrator_unknown_evaluation_no_op():
    questions = [{"id": "q1", "text": "Q1", "topic_name": "T1"}]
    orc = InterviewOrchestrator(questions)
    orc.record_turn("unknown_eval")
    assert orc.turns_in_question == 1
    assert orc.hints_given == 0
    assert orc.current_idx == 0


def test_orchestrator_max_hints_default():
    questions = [{"id": "q1", "text": "Q1"}]
    orc = InterviewOrchestrator(questions)
    assert orc.max_hints == 2


def test_get_next_topic_name_single_question():
    questions = [{"id": "q1", "text": "Q1", "topic_name": "Only Topic"}]
    orc = InterviewOrchestrator(questions)
    assert orc.get_next_topic_name() is None


def test_orchestrator_summary_includes_all_fields():
    questions = [{"id": "q1", "text": "Q1", "topic_name": "T1"}]
    orc = InterviewOrchestrator(questions)
    orc.record_turn("ambiguous")
    orc.record_turn("incorrect")
    orc.record_turn("correct")
    summary = orc.question_summaries[0]
    assert summary["question_id"] == "q1"
    assert summary["final_evaluation"] == "correct"
    assert summary["total_turns"] == 3
    assert summary["hints_used"] == 1
    assert summary["clarifications_used"] == 1
    assert summary["was_force_skipped"] is False
