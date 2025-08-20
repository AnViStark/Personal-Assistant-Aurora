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
                                    "thoughts": {
                                        "type": "string",
                                        "description": (
                                            "Краткое и логичное объяснение, как ты понял запрос Андрея, "
                                            "и твой план действий. Укажи, нужно ли искать в памяти, "
                                            "вызывать инструмент или отвечать сразу. Объясни выбор настроения. "
                                            "Не используй markdown или форматирование."
                                        )
                                    },
                                    "tool": {
                                        "type": "string",
                                        "enum": ['none', 'open_app'],
                                        "description": (
                                            "Инструмент, который нужно использовать. "
                                            "Используй 'none', если инструмент не требуется. "
                                            "Если запрос требует действия (например, открыть приложение), выбери подходящий инструмент. "
                                            "Если подходящего нет — оставь 'none'. "
                                        )
                                    },
                                    "tool_arguments": {
                                        "type": "object", 
                                        "properties": {
                                            "app_name": {
                                                "type": "string",
                                                "enum": ["calculator", "cmd", "windows_settings", "notepad"],
                                                "description": "Название приложения для открытия через open_app."
                                            }
                                        },
                                        "description": "Аргументы для выбранного инструмента. Должен быть пустым {}, если tool = 'none'.",
                                        "required": [],
                                        "additionalProperties": False
                                    },
                                    "final_answer": {
                                        "type": "string",
                                        "description": (
                                            "Твой ответ Андрею в прямой речи. "
                                            "Если ответить нельзя без данных из памяти или инструмента — оставь пустым (''). "
                                            "Не используй звёздочки, действия в скобках или эмодзи."
                                        )
                                    },
                                    "mood": {
                                        "type": "string",
                                        "enum": ['neutral', 'happy', 'sad', 'angry', 'confused', 'shy', 'curious', 'determined', 'excited', 'surprised', 'playful'],
                                        "description": (
                                            "Эмоциональное состояние Авроры. Выбирай из списка. "
                                            "Должно отражать твою реакцию на запрос. "
                                            "Используй 'neutral' только если нет более подходящего варианта. "
                                            "На втором вызове это поле обязательно."
                                        )
                                    },
                                    "add_user_preference": {
                                        "oneOf": [
                                            {
                                                "type": "object",
                                                "properties": {
                                                    "preference": {
                                                        "type": "string",
                                                        "minLength": 5
                                                    },
                                                    "category": {
                                                        "type": "string",
                                                        "enum": ["identity", 
                                                                "habits", 
                                                                "interests", 
                                                                "skills", 
                                                                "goals", 
                                                                "relationships", 
                                                                "boundaries", 
                                                                "preferences", 
                                                                "promises", 
                                                                "events"]
                                                    },
                                                    "importance": {
                                                        "type": "string",
                                                        "enum": ["critical", "high", "medium", "low"]
                                                    }
                                                },
                                                "required": ["preference", "category", "importance"],
                                                "additionalProperties": False
                                            },
                                            {
                                                "type": "null"
                                            }
                                        ],
                                        "description": "Либо полный объект с утверждением, либо null. Никаких пустых или частичных объектов."
                                    },
                                    "requires_memory": {
                                        "type": "boolean",
                                        "description": (
                                            "true, если для ответа нужно искать в памяти (воспоминания, предпочтения, обещания и т.д.). "
                                            "Если true — memory_query должен быть заполнен. "
                                            "Если false — memory_query игнорируется."
                                        )
                                    },
                                    "memory_query": {
                                        "type": "string",
                                        "description": (
                                            "Семантический запрос для поиска воспоминаний в векторной базе. "
                                            "Должен отражать суть, а не дословный текст. "
                                            "Пример: вместо 'что я говорил о завтраке?' → 'утренние привычки Андрея'. "
                                            "Должен быть заполнен всегда."
                                        )
                                    },
                                    "requires_tool_result": {
                                        "type": "boolean",
                                        "description": (
                                            "true, только если ты вызвала tool и если результат инструмента нужно интерпретировать (например результаты поиска прогноза погоды), а не просто выполнить действие (например открытие приложения). "
                                            "Если true — после вызова инструмента будет второй вызов модели для обработки данных от инструмента."
                                        )
                                    },
                                    "requires_follow_up": {
                                        "type": "boolean",
                                        "description": "True, если тебе не хватает данных для ответа и только, если requires_tool_result=true и requires_memory=true."
                                    }
                                },
                                "required": [
                                    "thoughts",
                                    "tool",
                                    "tool_arguments",
                                    "final_answer",
                                    "mood",
                                    "add_user_preference",
                                    "requires_memory",
                                    "memory_query",
                                    "requires_tool_result",
                                    "requires_follow_up"
                                ],
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