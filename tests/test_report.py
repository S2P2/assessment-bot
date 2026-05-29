import os
import json
import pytest
from unittest.mock import MagicMock, patch

from src.orchestrator import InterviewOrchestrator
from src.report import _build_score, _build_question_breakdown, generate_report, save_report


def _sample_questions():
    return [
        {
            "id": "sql-1",
            "topic_name": "SQL Basics",
            "text": "How do you find unique values in a column?",
            "criteria": "Must use the DISTINCT keyword.",
            "hint_guidelines": "Nudge them toward uniqueness.",
        },
        {
            "id": "sql-2",
            "topic_name": "SQL Basics",
            "text": "What is the difference between an INNER JOIN and a LEFT JOIN?",
            "criteria": "Must explain matching vs non-matching rows.",
            "hint_guidelines": "Ask about rows without matches.",
        },
        {
            "id": "python-1",
            "topic_name": "Python Basics",
            "text": "How do you handle exceptions?",
            "criteria": "Must mention try and except.",
            "hint_guidelines": "Ask about block-based error handling.",
        },
    ]


def _completed_orchestrator(questions):
    orc = InterviewOrchestrator(questions)
    # Simulate completing all questions
    for i, q in enumerate(questions):
        evaluations = ["correct", "incorrect", "ambiguous"]
        command = "NEXT_QUESTION"
        orc.history.append(f"User: answer for {q['id']}")
        orc.history.append(f"Interviewer: response for {q['id']}")
        orc.record_turn(command, evaluations[i])
    return orc


# --- _build_score ---


class TestBuildScore:
    def test_all_correct(self):
        summaries = [
            {"final_evaluation": "correct"},
            {"final_evaluation": "correct"},
        ]
        counts, total = _build_score(summaries)
        assert counts == {"correct": 2, "incorrect": 0, "ambiguous": 0}
        assert total == 2

    def test_mixed(self):
        summaries = [
            {"final_evaluation": "correct"},
            {"final_evaluation": "incorrect"},
            {"final_evaluation": "ambiguous"},
        ]
        counts, total = _build_score(summaries)
        assert counts == {"correct": 1, "incorrect": 1, "ambiguous": 1}
        assert total == 3

    def test_empty(self):
        counts, total = _build_score([])
        assert counts == {"correct": 0, "incorrect": 0, "ambiguous": 0}
        assert total == 0


# --- _build_question_breakdown ---


class TestBuildQuestionBreakdown:
    def test_includes_question_text(self):
        questions = _sample_questions()
        summaries = [{"question_id": "sql-1", "final_evaluation": "correct", "hints_used": 0, "total_turns": 1, "was_force_skipped": False}]
        lines = _build_question_breakdown(summaries, questions)
        text = "\n".join(lines)
        assert "How do you find unique values" in text
        assert "correct" in text

    def test_skipped_question(self):
        questions = _sample_questions()
        summaries = [{"question_id": "sql-1", "final_evaluation": "incorrect", "hints_used": 2, "total_turns": 3, "was_force_skipped": True}]
        lines = _build_question_breakdown(summaries, questions)
        text = "\n".join(lines)
        assert "skipped" in text

    def test_unknown_question_id(self):
        summaries = [{"question_id": "unknown-1", "final_evaluation": "correct", "hints_used": 0, "total_turns": 1, "was_force_skipped": False}]
        lines = _build_question_breakdown(summaries, [])
        text = "\n".join(lines)
        assert "unknown-1" in text


# --- generate_report ---


class TestGenerateReport:
    def test_basic_report_no_summary_bot(self):
        questions = _sample_questions()
        orc = _completed_orchestrator(questions)
        report = generate_report(orc, questions, "testuser", "test-interview")
        assert "# Interview Report" in report
        assert "**Candidate:** testuser" in report
        assert "**Interview:** test-interview" in report
        assert "1 correct, 1 incorrect, 1 ambiguous" in report
        assert "sql-1" in report
        assert "python-1" in report

    def test_report_with_summary_bot(self):
        questions = _sample_questions()
        orc = _completed_orchestrator(questions)

        mock_result = MagicMock()
        mock_result.verdict = MagicMock()
        mock_result.verdict.topic_observations = [
            MagicMock(topic="SQL Basics", strengths="Good joins", weaknesses="Weak on DISTINCT"),
            MagicMock(topic="Python Basics", strengths="Solid error handling", weaknesses="None observed"),
        ]
        mock_result.verdict.overall_verdict = "Solid fundamentals, needs more SQL practice."

        mock_bot = MagicMock(return_value=mock_result)

        report = generate_report(orc, questions, "testuser", "test-interview", summary_bot=mock_bot)
        assert "## Improvement Summary" in report
        assert "SQL Basics" in report
        assert "Good joins" in report
        assert "Solid fundamentals, needs more SQL practice." in report

    def test_report_graceful_summary_failure(self):
        questions = _sample_questions()
        orc = _completed_orchestrator(questions)

        mock_bot = MagicMock(side_effect=RuntimeError("LLM down"))

        report = generate_report(orc, questions, "testuser", "test-interview", summary_bot=mock_bot)
        assert "Summary generation failed" in report
        # Score and breakdown should still be present
        assert "1 correct, 1 incorrect, 1 ambiguous" in report


# --- save_report ---


class TestSaveReport:
    def test_creates_file(self, tmp_path):
        report_text = "# Test Report"
        filepath = save_report(report_text, "testuser", reports_dir=str(tmp_path))
        assert os.path.exists(filepath)
        with open(filepath, encoding="utf-8") as f:
            assert f.read() == "# Test Report"

    def test_sanitizes_filename(self, tmp_path):
        filepath = save_report("report", "user/evil<>name", reports_dir=str(tmp_path))
        assert "user_evil__name.md" in filepath

    def test_creates_directory(self, tmp_path):
        reports_dir = os.path.join(str(tmp_path), "nested", "reports")
        filepath = save_report("report", "testuser", reports_dir=reports_dir)
        assert os.path.exists(filepath)

    def test_overwrites_existing(self, tmp_path):
        save_report("v1", "testuser", reports_dir=str(tmp_path))
        filepath = save_report("v2", "testuser", reports_dir=str(tmp_path))
        with open(filepath, encoding="utf-8") as f:
            assert f.read() == "v2"
