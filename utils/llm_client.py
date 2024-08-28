import os
from anthropic import AnthropicVertex

class LLMClient:
    def __init__(self):
        self.project_id = os.getenv("PROJECT_ID")
        self.location = os.getenv("LOCATION")
        self.model = os.getenv("MODEL")
        self.client = AnthropicVertex(region=self.location, project_id=self.project_id)

    def call_llm(self, system_prompt, user_prompt, max_tokens=1024):
        try:
            response = self.client.messages.create(
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                model=self.model,
            )
            return response.content[0].text
        except Exception as e:
            print(f"An error occurred while calling the LLM: {e}")
            return None