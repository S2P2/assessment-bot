import dspy
import os
from src.data import load_questions
from src.orchestrator import InterviewOrchestrator
from src.modules import InterviewBot

def main():
    # Setup
    # Ensure OPENAI_API_KEY is in environment or use a dummy if just testing structure
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY not found in environment.")
    
    lm = dspy.LM('openai/gpt-4o-mini', api_key=api_key)
    dspy.configure(lm=lm)
    
    data = load_questions("questions.json")
    # Flatten questions for the orchestrator (POC simplification)
    all_questions = []
    for topic in data["topics"]:
        for q in topic["questions"]:
            q["topic_name"] = topic["topic_name"]
            all_questions.append(q)
            
    orc = InterviewOrchestrator(all_questions)
    bot = InterviewBot()
    
    print(f"--- Starting Interview: {data['interview_id']} ---")
    
    while True:
        q = orc.get_current_question()
        if not q:
            break
            
        print(f"\n[{q['topic_name']}] Interviewer: {q['text']}")
        user_input = input("You: ")
        
        # Call DSPy
        result = bot(
            topic=q['topic_name'],
            question=q['text'],
            criteria=q['criteria'],
            hint_guidelines=q['hint_guidelines'],
            history=orc.history[-5:],
            user_input=user_input,
            attempt_number=orc.attempts
        )
        
        action = result.action
        command = action.command
        
        # Orchestrator Override
        if orc.should_force_skip() and command == "GIVE_HINT":
            command = "PROMPT_SKIP"
            print("\n(System: Maximum attempts reached. Suggesting skip.)")
            
        print(f"\nInterviewer: {action.response}")
        
        orc.history.append(f"User: {user_input}")
        orc.history.append(f"Interviewer: {action.response}")
        orc.handle_command(command)

    print("\n--- Interview Complete ---")

if __name__ == "__main__":
    main()
