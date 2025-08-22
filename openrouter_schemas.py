AURORA_SCHEMA = {
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
                                            "planned_events"]
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
                "requires_tool_result": {
                    "type": "boolean",
                    "description": (
                        "true, только если ты вызвала tool и если результат инструмента нужно интерпретировать (например результаты поиска прогноза погоды), а не просто выполнить действие (например открытие приложения). "
                        "Если true — после вызова инструмента будет второй вызов модели для обработки данных от инструмента."
                    )
                },
                "requires_follow_up": {
                    "type": "boolean",
                    "description": "True, если тебе не хватает данных для ответа и только, если requires_tool_result=true"
                }
            },
            "required": [
                "thoughts",
                "tool",
                "tool_arguments",
                "final_answer",
                "mood",
                "requires_tool_result",
                "requires_follow_up"
            ],
            "additionalProperties": False
        }
    }
}

MEMORY_AGENT_PLANNING_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "memory_agent_planning",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "thoughts": {"type": "string"},
                "is_new_info": {"type": "boolean"},
                "new_memory_record": {
                    "oneOf": [{"type": "string"}, {"type": "null"}]
                },
                "category": {
                    "oneOf": [
                        {"type": "string", ""
                        "enum": ["identity", "habits", "interests", "skills", "goals", "relationships", "boundaries", "preferences", "promises", "planned_events"]},
                        {"type": "null"}
                    ]
                },
                "importance": {
                    "oneOf": [
                        {"type": "string", 
                         "enum": ["critical", "high", "medium", "low"]},
                        {"type": "null"}
                    ]
                },
                "requires_memory": {"type": "boolean"},
                "memory_query": {"type": "string"}
            },
            "required": ["thoughts", "is_new_info", "new_memory_record", "category", "importance", "requires_memory", "memory_query"],
            "additionalProperties": False
        }
    }
}

MEMORY_AGENT_FINAL_SCHEMA = {
    "name": "memory_manager_response",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "relevant_memories": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "text": {"type": "string"},
                        "category": {"type": "string"},
                        "importance": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"]
                        }
                    },
                    "required": ["id", "text", "category", "importance"],
                    "additionalProperties": False
                },
                "description": "Список релевантных воспоминаний для контекста. Может быть пустым."
            },
            "new_memory_action": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "update", "skip"]
                    },
                    "old_memory_id": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "null"}
                        ]
                    },
                    "new_memory": {
                        "oneOf": [
                            {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "category": {
                                        "type": "string",
                                        "enum": [
                                            "identity", "habits", "interests", "skills",
                                            "goals", "relationships", "boundaries",
                                            "preferences", "planned_events"
                                        ]
                                    },
                                    "importance": {
                                        "type": "string",
                                        "enum": ["critical", "high", "medium", "low"]
                                    }
                                },
                                "required": ["text", "category", "importance"],
                                "additionalProperties": False
                            },
                            {
                                "type": "null"
                            }
                        ]
                    }
                },
                "required": ["action", "old_memory_id", "new_memory"],
                "additionalProperties": False,
                "description": "Решение по новому воспоминанию: создать, обновить или пропустить."
            }
        },
        "required": ["relevant_memories", "new_memory_action"],
        "additionalProperties": False
    }
}