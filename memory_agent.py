from openrouter_client import OpenRouterClient
from chroma_mem import ChromaHandler
from openrouter_schemas import MEMORY_AGENT_FINAL_SCHEMA, MEMORY_AGENT_PLANNING_SCHEMA
from memory_agent_prompts import MEMORY_AGENT_PLANNING_PROMPT, MEMORY_AGENT_FINAL_PROMPT

class MemoryAgent():
    def __init__(self, client: OpenRouterClient, chroma: ChromaHandler, model_name: str = "deepseek/deepseek-chat-v3-0324:free"):
        self.client = client
        self.chroma = chroma
        self.model_name = model_name

    def build_system_prompt(self, memory_step, user_request: str, dialogue_context: list = None, first_step_response: dict = None):
        prompt_parts = []
        
        if memory_step == MEMORY_AGENT_PLANNING_PROMPT:
            # Собираем контекст
            history_parts = []
            start_idx = max(0, len(dialogue_context) - 11)
            for msg in dialogue_context[start_idx:-1]:  # все кроме последнего (это user_request)
                history_parts.append(f"{msg['role']}: {msg['content']}")
            history = "Последние сообщения в диалоге: " + ". ".join(history_parts) + "."
            history += f" Сейчас пользователь написал: '{user_request}'."

            prompt_parts.append(MEMORY_AGENT_PLANNING_PROMPT)
            prompt_parts.append(history)
            return "\n\n".join(prompt_parts)

        elif memory_step == MEMORY_AGENT_FINAL_PROMPT:
            query = first_step_response.get("memory_query", "").strip()
            if not query:
                relevant_memories = []
            else:
                relevant_memories = self.chroma.search_memory(query)
            prompt_parts.append(MEMORY_AGENT_FINAL_PROMPT)
            prompt_parts.append(f"Сейчас пользователь написал: '{user_request}'.")

            if first_step_response.get("is_new_info"):
                new_memory_record = first_step_response.get("new_memory_record")
                category = first_step_response.get("category")
                importance = first_step_response.get("importance")
                prompt_parts.append(
                    f"Предложена следующая запись для добавления в память: "
                    f"new_memory_record: {new_memory_record}, category: {category}, importance: {importance}."
                )
                prompt_parts.append(
                    f"В памяти найдены следующие записи, похожие семантически по смыслу на новое воспоминание: {relevant_memories}"
                )

            elif first_step_response.get("requires_memory"):
                prompt_parts.append(
                    f"В памяти найдены следующие записи, похожие семантически по смыслу на новую реплику пользователя: {relevant_memories}"
                )

            return "\n\n".join(prompt_parts)
    
    def activate_memory_agent(self, user_request, dialogue_context, memory_step, first_step_response):
        if memory_step == 1:
            system_prompt = self.build_system_prompt(memory_step, user_request, dialogue_context)
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            answer = self.client.chat_completion(self.model_name, messages, MEMORY_AGENT_PLANNING_SCHEMA)
            return answer
        if memory_step == 2:
            system_prompt = self.build_system_prompt(memory_step, user_request, dialogue_context, first_step_response)
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            answer = self.client.chat_completion(self.model_name, messages, MEMORY_AGENT_FINAL_SCHEMA)
            return answer




        