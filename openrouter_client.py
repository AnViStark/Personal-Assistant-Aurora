from openai import OpenAI
import json
from openrouter_schemas import AURORA_SCHEMA, MEMORY_AGENT_FINAL_SCHEMA, MEMORY_AGENT_PLANNING_SCHEMA

class OpenRouterClient():
    def __init__(self, openrouter_key):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key,
        )
    
    def chat_completion(self, model: str, messages: list, schema: dict = None):
        try:
            completion = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.55,
                    top_p=0.9,
                    frequency_penalty=0.4,
                    presence_penalty=0.6,
                    extra_body={
                        "provider": {
                            "order": ["Chutes"],
                            "allow_fallbacks": False
                        }
                    },
                    response_format = schema
            )
            result = json.loads(completion.choices[0].message.content)
            return result
        except Exception as e:
            return f"Ошибка API: {str(e)}"