from pydantic import BaseModel

class QuestionInputFormat(BaseModel):
    question_no: int
    question: str


class ResponseOutputFormat(BaseModel):
    question_no: int
    response: str