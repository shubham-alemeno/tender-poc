from typing import List, Dict
from utils.markdown_utils import PDFMarkdown
from utils.llm_client import LLMClient
from utils.models import QuestionInputFormat, ResponseOutputFormat
from utils.response_processing import process_response

class BidDocument(PDFMarkdown):
    def __init__(self, pdf_path: str, file_id: str):
        super().__init__(pdf_path, file_id)
        self.llm_client = LLMClient()

    def query(self, question: str) -> str:
        """
        Takes a single question and provides a response using long context LLM.
        
        :param question: A string containing the question to be answered.
        :return: A string containing the response from the LLM.
        """
        system_prompt = f"Here's the content of the file:\n\n{self.content}\n\nPlease answer the following question based on this content:"
        user_prompt = question

        response_content = self.llm_client.call_llm(system_prompt, user_prompt)

        if response_content:
            return response_content.strip()
        else:
            return "Failed to get a response from the LLM."

    def queryList(self, questions: List[QuestionInputFormat]) -> List[ResponseOutputFormat]:
        """
        Takes a list of questions in input format and answers them, returns an object in appropriate format.
        
        :param questions: A list of QuestionInputFormat objects containing the questions to be answered.
        :return: A list of ResponseOutputFormat objects containing the responses.
        """
        system_prompt = f"Here's the content of the file:\n\n{self.content}\n\nPlease answer the following questions based on this content:"
        user_prompt = [q.model_dump() for q in questions]

        response_content = self.llm_client.call_llm(system_prompt, str(user_prompt))

        if response_content:
            processed_responses = process_response(response_content)
            return [ResponseOutputFormat(question_no=r['question_no'], response=r['response']) for r in processed_responses]
        else:
            return [ResponseOutputFormat(question_no=q.question_no, response="Failed to get a response from the LLM.") for q in questions]