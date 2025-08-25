from openrouter_client import OpenRouterClient
from chroma_mem import ChromaHandler
from openrouter_schemas import MEMORY_AGENT_FINAL_SCHEMA, MEMORY_AGENT_PLANNING_SCHEMA
from memory_agent_prompts import MEMORY_AGENT_PLANNING_PROMPT, MEMORY_AGENT_FINAL_PROMPT

class MemoryAgent():
    def __init__(self, client: OpenRouterClient, chroma: ChromaHandler, model_name: str = "openai/gpt-oss-20b:free"):
        self.client = client
        self.chroma = chroma
        self.model_name = model_name

    def build_system_prompt(self, memory_step, user_request: str, dialogue_context: list = None, first_step_response: dict = None):
        prompt_parts = []
        
        if memory_step == MEMORY_AGENT_PLANNING_PROMPT:
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
                    f"В памяти найдены следующие записи, похожие семантически: {relevant_memories}"
                )

            elif first_step_response.get("requires_memory"):
                prompt_parts.append(
                    f"В памяти найдены следующие записи, релевантные новой реплике: {relevant_memories}"
                )

            return "\n\n".join(prompt_parts)
    
    def activate_memory_agent_phase1(self, user_request, dialogue_context):
        system_prompt = self.build_system_prompt(MEMORY_AGENT_PLANNING_PROMPT, user_request, dialogue_context)
        messages = [{"role": "system", "content": system_prompt}]
        
        print("\n[MemoryAgent:Phase1] Отправляем промпт:")
        print(dialogue_context)
        
        response = self.client.chat_completion(
            self.model_name,
            messages,
            schema=MEMORY_AGENT_PLANNING_SCHEMA
        )
        
        print("\n[MemoryAgent:Phase1] Полный ответ API:")
        print(response)
        return response

    def activate_memory_agent_phase2(self, user_request, dialogue_context, first_step_response):
        system_prompt = self.build_system_prompt(
            MEMORY_AGENT_FINAL_PROMPT,
            user_request,
            dialogue_context,
            first_step_response
        )
        messages = [{"role": "system", "content": system_prompt}]
        
        print("\n[MemoryAgent:Phase2] Отправляем промпт:")
        print(dialogue_context)

        second_response = self.client.chat_completion(
            self.model_name,
            messages,
            schema=MEMORY_AGENT_FINAL_SCHEMA
        )
        
        print("\n[MemoryAgent:Phase2] Полный ответ API:")
        print(second_response)

        # --- Сохраняем новую информацию в память ---
        if first_step_response.get("is_new_info"):
            self.apply_memory_action(second_response)
            print("[MemoryAgent] Новая информация сохранена в память.")

        # --- Отдаём релевантные старые записи для Авроры ---
        relevant_memories = []
        if first_step_response.get("requires_memory"):
            relevant_memories = second_response.get("relevant_memories", [])
            print(f"[MemoryAgent] Передаем Авроре релевантные старые записи: {relevant_memories}")

        return relevant_memories
            
    def apply_memory_action(self, action_response: dict):
        print("\n[MemoryAgent] Разбираем действие с памятью...")
        new_action = action_response.get("new_memory_action", {})
        relevant_memories = action_response.get("relevant_memories", [])
        
        if not new_action:
            print("[MemoryAgent] Нет данных для действия с памятью")
            return relevant_memories

        action = new_action.get("action")
        old_id = new_action.get("old_memory_id")
        new_memory = new_action.get("new_memory")

        print(f"[MemoryAgent] Действие: {action}, old_id={old_id}, new_memory={new_memory}")

        if action == "update" and new_memory:
            if old_id:
                self.chroma.delete_record(old_id)
                print(f"[MemoryAgent] Удалена старая запись: {old_id}")
            self.chroma.add_record(
                text=new_memory["text"],
                category=new_memory["category"],
                importance=new_memory["importance"]
            )
            print(f"[MemoryAgent] Добавлена новая запись: {new_memory['text']}")

        elif action == "create" and new_memory:
            self.chroma.add_record(
                text=new_memory["text"],
                category=new_memory["category"],
                importance=new_memory["importance"]
            )
            print(f"[MemoryAgent] Добавлена новая запись: {new_memory['text']}")

        elif action == "skip":
            print("[MemoryAgent] Новая запись пропущена (дубль или неактуальна)")

        return relevant_memories
