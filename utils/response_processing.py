import os
import json
from typing import List
from datetime import datetime
from utils.models import QuestionInputFormat

def save_chat_history(file_path: str, questions: List[QuestionInputFormat], responses: List[dict]):
    """Save chat history to a JSON file."""
    chat_history = {
        "timestamp": datetime.now().isoformat(),
        "file_processed": os.path.basename(file_path),
        "questions_and_answers": [
            {
                "question_no": q.question_no,
                "question": q.question,
                "response": r["response"]
            } for q, r in zip(questions, responses)
        ]
    }
    with open("chat_history.json", "w") as json_file:
        json.dump(chat_history, json_file, indent=2)
    print("Chat history saved to 'chat_history.json'")

def process_response(response_content: str) -> List[dict]:
    """Process the raw response content and extract structured responses."""
    responses = []
    current_question = 0
    current_response = ""
    
    for line in response_content.split('\n'):
        line = line.strip()
        if line.startswith(f"{current_question + 1}.") or line.startswith(f"Question {current_question + 1}:"):
            if current_response:
                responses.append({"question_no": current_question, "response": current_response.strip()})
            current_question += 1
            current_response = line.split(":", 1)[-1].strip()
        else:
            current_response += " " + line

    if current_response:
        responses.append({"question_no": current_question, "response": current_response.strip()})
    
    return responses