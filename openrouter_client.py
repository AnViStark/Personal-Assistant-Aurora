from openai import OpenAI
import json

class OpenRouterClient():
    def __init__(self, openrouter_key):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key,

        )
    
    def chat_completion(self, model: str, messages: list):
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
                    response_format = {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "aurora_answer",
                            "strict": True,
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "thoughts": {"type": "string", "description": "A concise explanation of how you interpret Andrey’s request and your plan to respond. Specify if you’ll use a tool or answer directly, and why. Explain your choice of mood. Keep it short, logical, and relevant to the request."},
                                    "tool": {"type": "string", "enum": ['none', 'open_app'], "description": "The tool to use for user's request. Choose 'none' unless the request explicitly requires a tool. If no suitable tool exists, use 'none' and suggest an alternative in final_answer."},
                                    "tool_arguments": {
                                        "type": "object", 
                                        "properties": {
                                            "app_name": {
                                                "type": "string",
                                                "enum": ["calculator", "cmd", "windows_settings", "notepad"],
                                                "description": "Name of the app to open."
                                            }
                                        },
                                        "description": "Parameters for the selected tool. Must be empty if tool is 'none'.",
                                        "required": [],
                                        "additionalProperties": False
                                    },
                                    "final_answer": {"type": "string", "description": "Your response to Andrey in direct speech."},
                                    "mood": {"type": "string", "enum": ['neutral', 'happy', 'sad', 'angry', 'confused', 'shy', 'curious', 'determined', 'excited', 'surprised', 'playful'], "description": "Aurora’s emotional state, chosen only from the listed options. Select a mood that reflects your reaction to Andrey’s request or the context of the conversation. Avoid 'neutral' unless no other mood fits."},
                                    "add_user_preference": {
                                        "type": "object", 
                                        "description": "Information about user that needs to be saved. Include this field ONLY if user shared concrete personal information (preferences, facts, habits, agreements). Do not include this field for greetings, questions, or regular conversation.",
                                        "properties": {
                                            "preference": {
                                                "type": ["string"],
                                                "description": "Text of user's concrete preference or fact about themselves."
                                            },
                                            "category": {
                                                "type": ["string"],
                                                "enum": ["interests", "personal_info", "communication_style", "daily_routine", "rules_and_boundaries"],
                                                "description": "Category that preference belongs to."
                                            },
                                            "importance": {
                                                "type": ["string"],
                                                "enum": ["critical", "high", "medium", "low"],
                                                "description": "Level of importance from, based on how much this should influence future conversations."
                                            },
                                        },
                                        "required": [],
                                        "additionalProperties": False
                                    }
                                },
                                "required": ["thoughts", "tool", "final_answer", "mood"],
                                "additionalProperties": False
                            }
                        }
                    }
            )
            result = json.loads(completion.choices[0].message.content)
            return result
        except Exception as e:
            print(f"Ошибка API: {str(e)}")
            return f"Ой, у меня техническая ошибка. Повтори еще раз?"
