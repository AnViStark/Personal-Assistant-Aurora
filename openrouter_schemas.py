AURORA_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "aurora_final_answer",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "thoughts": {
                    "type": "string",
                    "description": (
                        "Объяснение, как ты поняла запрос, почему выбрала такое настроение, "
                        "как использовала контекст из памяти и времени. Без форматирования."
                    )
                },
                "final_answer": {
                    "type": "string",
                    "description": (
                        "Твой ответ пользователю от первого лица. "
                        "Не используй действия в скобках, эмодзи или markdown."
                    )
                },
                "mood": {
                    "type": "string",
                    "enum": [
                        'neutral', 'happy', 'sad', 'angry', 'confused', 'shy', 'curious',
                        'determined', 'excited', 'surprised', 'playful'
                    ],
                    "description": "Эмоциональное состояние Авроры, соответствующее тону ответа."
                }
            },
            "required": ["thoughts", "final_answer", "mood"],
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
                        {
                            "type": "string",
                            "enum": [
                                "identity", "habits", "interests", "skills", "goals",
                                "relationships", "boundaries", "preferences",
                                "promises", "planned_events"
                            ]
                        },
                        {"type": "null"}
                    ]
                },
                "importance": {
                    "oneOf": [
                        {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"]
                        },
                        {"type": "null"}
                    ]
                },
                "requires_memory": {"type": "boolean"},
                "memory_query": {"type": "string"}
            },
            "required": [
                "thoughts", "is_new_info", "new_memory_record", "category",
                "importance", "requires_memory", "memory_query"
            ],
            "additionalProperties": False
        }
    }
}


MEMORY_AGENT_FINAL_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
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
                                {"type": "null"}
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
}
