import os
from anthropic import Anthropic
from dotenv import load_dotenv

class LLMClient:
    def __init__(self, anthropic_model=None):
        load_dotenv()
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.default_model = anthropic_model or os.getenv("ANTHROPIC_MODEL")
        self.client = Anthropic(api_key=self.api_key)

    def call_llm(self, system_prompt, user_prompt, model=None, max_tokens=1024):
        try:
            response = self.client.messages.create(
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                model=model or self.default_model,
            )
            return response.content[0].text
        except Exception as e:
            print(f"An error occurred while calling the LLM: {e}")
            return None