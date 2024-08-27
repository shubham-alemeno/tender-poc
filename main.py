import os
import json
from typing import List
from dotenv import load_dotenv
from datetime import datetime
from pydantic import BaseModel
from anthropic import AnthropicVertex
from utils.markdown_utils import pdf_to_markdown

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
MODEL = os.getenv("MODEL")

class QuestionInputFormat(BaseModel):
    question_no: int
    question: str

class ResponseOutputFormat(BaseModel):
    question_no: int
    response: str

def get_file_path(is_pdf: bool = False) -> str:
    """Prompt user for file path and validate its existence."""
    file_type = "PDF" if is_pdf else "Markdown"
    while True:
        file_path = input(f"Enter the path to the {file_type} file: ")
        if os.path.exists(file_path):
            return file_path
        print(f"File not found. Please enter a valid {file_type} file path.")

def process_file(file_path: str, is_pdf: bool) -> str:
    """Process the input file and return its content."""
    file_name = os.path.basename(file_path)
    print(f"Processing file: {file_name}")
    
    if is_pdf:
        markdown_file = f"{os.path.splitext(file_name)[0]}.md"
        pdf_to_markdown(file_path, markdown_file)
        file_path = markdown_file
    
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    print("File content preview:")
    print("\n".join(content.split("\n")[:3]))
    return content

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

def main():
    client = AnthropicVertex(region=LOCATION, project_id=PROJECT_ID)

    is_pdf = input("Do you want to process a PDF file? (y/n): ").lower() == 'y'
    file_path = get_file_path(is_pdf)
    file_content = process_file(file_path, is_pdf)

    while True:
        try:
            num_questions = int(input("How many pre-questions do you want to ask? "))
            if num_questions <= 0:
                raise ValueError("Number of questions must be positive.")
            break
        except ValueError as e:
            print(f"Invalid input: {e}. Please enter a positive number.")

    questions = [
        QuestionInputFormat(question_no=i+1, question=input(f"Enter question {i+1}: "))
        for i in range(num_questions)
    ]

    system_prompt = f"Here's the content of the file:\n\n{file_content}\n\nPlease answer the following questions based on this content:"

    try:
        with client.messages.stream(
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": json.dumps([q.dict() for q in questions])}],
            model=MODEL,
        ) as stream:
            print("Response:")
            response_content = "".join(text for text in stream.text_stream)
            print(response_content)

        print("\nRaw response content:")
        print(response_content)

        responses = process_response(response_content)
        save_chat_history(file_path, questions, responses)

    except AnthropicVertex.APIError as e:
        print(f"API Error occurred: {e}")
    except AnthropicVertex.APIConnectionError as e:
        print(f"API Connection Error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print(f"Current working directory: {os.getcwd()}")
        print("Attempting to save error log...")
        with open("error_log.txt", "w") as error_file:
            error_file.write(f"Error: {str(e)}\n")
            error_file.write(f"Response content: {response_content}\n")
        print("Error log saved as 'error_log.txt'")

if __name__ == "__main__":
    main()