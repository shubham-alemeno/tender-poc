import json
from dotenv import load_dotenv
from utils.models import QuestionInputFormat, ResponseOutputFormat
from utils.llm_client import LLMClient
from utils.file_processing import get_file_path, process_file
from utils.response_processing import process_response, save_chat_history

load_dotenv()

def main():
    llm_client = LLMClient()

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
    user_prompt = json.dumps([q.model_dump() for q in questions])

    response_content = llm_client.call_llm(system_prompt, user_prompt)

    if response_content:
        print("Response:")
        print(response_content)

        print("\nRaw response content:")
        print(response_content)

        responses = process_response(response_content)
        save_chat_history(file_path, questions, responses)
    else:
        print("Failed to get a response from the LLM.")

if __name__ == "__main__":
    main()