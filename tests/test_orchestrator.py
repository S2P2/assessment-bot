from src.orchestrator import InterviewOrchestrator

def test_orchestrator_progression():
    questions = [{"id": "q1", "text": "Q1"}, {"id": "q2", "text": "Q2"}]
    orc = InterviewOrchestrator(questions)
    assert orc.get_current_question()["id"] == "q1"
    orc.handle_command("NEXT_QUESTION")
    assert orc.get_current_question()["id"] == "q2"
    assert orc.attempts == 0

def test_orchestrator_attempts():
    questions = [{"id": "q1", "text": "Q1"}]
    orc = InterviewOrchestrator(questions, max_attempts=2)
    orc.handle_command("GIVE_HINT")
    assert orc.attempts == 1
    assert orc.should_force_skip() is False
    orc.handle_command("GIVE_HINT")
    assert orc.attempts == 2
    assert orc.should_force_skip() is True

def test_orchestrator_get_next_topic_name():
    questions = [
        {"id": "q1", "text": "Q1", "topic_name": "Topic 1"},
        {"id": "q2", "text": "Q2", "topic_name": "Topic 2"},
    ]
    orc = InterviewOrchestrator(questions)
    
    # At index 0, next should be Topic 2
    assert orc.get_next_topic_name() == "Topic 2"
    
    # Move to index 1, next should be None
    orc.handle_command("NEXT_QUESTION")
    assert orc.get_next_topic_name() is None
