import json
import os

from src.modules import SummaryBot

BADGE_MAP = {
    "correct": "\u2713",
    "incorrect": "\u2717",
    "ambiguous": "~",
}


def _build_score(question_summaries):
    """Compute raw count aggregate from question summaries."""
    counts = {"correct": 0, "incorrect": 0, "ambiguous": 0}
    for s in question_summaries:
        ev = s.get("final_evaluation", "ambiguous")
        if ev in counts:
            counts[ev] += 1
    total = len(question_summaries)
    return counts, total


def _build_question_breakdown(question_summaries, questions):
    """Build per-question breakdown lines."""
    lines = []
    for s in question_summaries:
        qid = s.get("question_id", "?")
        ev = s.get("final_evaluation", "?")
        badge = BADGE_MAP.get(ev, "?")
        hints = s.get("hints_used", 0)
        skipped = s.get("was_force_skipped", False)

        # Find question text
        q_text = "?"
        for q in questions:
            if q.get("id") == qid:
                q_text = q["text"]
                break

        status = ev
        if skipped:
            status = "skipped"

        lines.append(f"### {badge} {qid}")
        lines.append(f"- **Question:** {q_text}")
        lines.append(f"- **Result:** {status}")
        lines.append(f"- **Hints used:** {hints}")
        lines.append(f"- **Turns:** {s.get('total_turns', '?')}")
        lines.append("")
    return lines


def generate_report(orc, questions, user_id, interview_id, summary_bot=None):
    """Generate a full interview report as markdown.

    Args:
        orc: InterviewOrchestrator with completed interview state.
        questions: Flattened question list (from data.py).
        user_id: Candidate identifier.
        interview_id: Interview identifier from questions.json.
        summary_bot: Optional SummaryBot instance. If None, improvement summary is skipped.

    Returns:
        str: The full report as markdown.
    """
    summaries = orc.question_summaries
    counts, total = _build_score(summaries)

    lines = []
    lines.append(f"# Interview Report")
    lines.append("")
    lines.append(f"- **Candidate:** {user_id}")
    lines.append(f"- **Interview:** {interview_id}")
    lines.append("")

    # Aggregate score
    lines.append("## Score")
    lines.append("")
    lines.append(
        f"**{counts['correct']} correct, "
        f"{counts['incorrect']} incorrect, "
        f"{counts['ambiguous']} ambiguous** out of {total}"
    )
    lines.append("")

    # Per-question breakdown
    lines.append("## Question Breakdown")
    lines.append("")
    lines.extend(_build_question_breakdown(summaries, questions))

    # Improvement summary via LLM
    if summary_bot is not None:
        try:
            result = summary_bot(
                question_summaries=json.dumps(summaries, indent=2),
                conversation_history="\n".join(orc.history),
            )
            verdict = result.verdict

            lines.append("## Improvement Summary")
            lines.append("")
            for obs in verdict.topic_observations:
                lines.append(f"### {obs.topic}")
                lines.append(f"- **Strengths:** {obs.strengths}")
                lines.append(f"- **Weaknesses:** {obs.weaknesses}")
                lines.append("")
            lines.append("### Overall")
            lines.append("")
            lines.append(verdict.overall_verdict)
            lines.append("")
        except Exception:
            # If LLM fails, still produce the report without the summary
            lines.append("## Improvement Summary")
            lines.append("")
            lines.append("_Summary generation failed. Raw scores are available above._")
            lines.append("")

    return "\n".join(lines)


def save_report(report_text, user_id, reports_dir="reports"):
    """Save report to a markdown file.

    Args:
        report_text: The markdown report.
        user_id: Used as the filename (sanitized).
        reports_dir: Directory for report files.

    Returns:
        str: Path to the saved file.
    """
    os.makedirs(reports_dir, exist_ok=True)

    # Sanitize user_id for filename
    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in user_id)
    filepath = os.path.join(reports_dir, f"{safe_name}.md")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_text)

    return filepath
