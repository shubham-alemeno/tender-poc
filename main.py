import json
from dotenv import load_dotenv
from utils.models import QuestionInputFormat, ResponseOutputFormat
from utils.llm_client import LLMClient
from utils.file_processing import get_file_path, process_file
from utils.response_processing import process_response, save_chat_history
from utils.bid_document import BidDocument

load_dotenv()

def main():
    is_pdf = input("Do you want to process a PDF file? (y/n): ").lower() == 'y'
    file_path = get_file_path(is_pdf)
    
    if is_pdf:
        bid_doc = BidDocument(file_path, "unique_file_id")
    else:
        print("This functionality is currently only available for PDF files.")
        return

    while True:
        print("\nWhat would you like to do?")
        print("1. Ask a single question")
        print("2. Ask multiple questions")
        print("3. Exit")
        
        choice = input("Enter your choice (1/2/3): ")

        if choice == '1':
            single_question = input("Enter your question: ")
            response = bid_doc.query(single_question)
            print(f"\nResponse: {response}")

        elif choice == '2':
            while True:
                try:
                    num_questions = int(input("How many questions do you want to ask? "))
                    if num_questions <= 0:
                        raise ValueError("Number of questions must be positive.")
                    break
                except ValueError as e:
                    print(f"Invalid input: {e}. Please enter a positive number.")

            questions = [
                QuestionInputFormat(question_no=i+1, question=input(f"Enter question {i+1}: "))
                for i in range(num_questions)
            ]

            responses = bid_doc.queryList(questions)
            
            print("\nResponses:")
            for resp in responses:
                print(f"Question {resp.question_no}: {resp.response}")

        elif choice == '3':
            print("Exiting the program.")
            break

        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()