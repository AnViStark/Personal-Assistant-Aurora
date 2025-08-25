from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel, QMainWindow, QSizePolicy
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
import re
from datetime import datetime
import json

from openrouter_schemas import AURORA_SCHEMA

from main_prompts import (
    PERSONALITY_PROMPT,
    FINAL_RESPONSE_PHASE_PROMPT,
    FINAL_EXAMPLES_PROMPT
)

MOOD_IMAGES = {
    "neutral": "mood_pic/neutral.png",
    "sad": "mood_pic/sad.png",
    "happy": "mood_pic/happy.png",
    "angry": "mood_pic/angry.png",
    "confused": "mood_pic/confused.png",
    "curious": "mood_pic/curious.png",
    "excited": "mood_pic/excited.png",
    "shy": "mood_pic/shy.png",
    "determined": "mood_pic/determined.png",
    "playful": "mood_pic/playful.png",
    "surprised": "mood_pic/surprised.png",
}


class MainWindow(QMainWindow):
    def __init__(self, client, mongodb, chroma_memory, memory_agent, audio_manager):
        super().__init__()
        self.client = client
        self.mongodb = mongodb
        self.chroma_memory = chroma_memory
        self.memory_agent = memory_agent
        self.audio_manager = audio_manager

        self.setWindowTitle("Аврора")
        self.resize(850, 700)

        self.setup_ui()
        self.set_mood("neutral")

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Картинка слева
        self.aurora_pic = QLabel()
        self.aurora_pic.setAlignment(Qt.AlignCenter)
        self.aurora_pic.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.aurora_pic.setMinimumSize(200, 200)
        self.aurora_pic.setScaledContents(True)

        # Чат справа
        chat_layout = QVBoxLayout()
        self.chat_window = QTextEdit(readOnly=True)
        chat_layout.addWidget(self.chat_window)

        entry_layout = QHBoxLayout()
        self.entry_field = QLineEdit()
        self.entry_field.returnPressed.connect(self.on_send_message)
        entry_layout.addWidget(self.entry_field)

        self.send_button = QPushButton("Отправить")
        self.send_button.clicked.connect(self.on_send_message)
        entry_layout.addWidget(self.send_button)

        self.clear_db_button = QPushButton("Очистить")
        self.clear_db_button.clicked.connect(lambda: self.mongodb.delete_all_records(self.mongodb.phrases))
        entry_layout.addWidget(self.clear_db_button)

        chat_layout.addLayout(entry_layout)
        main_layout.addWidget(self.aurora_pic, 1)
        main_layout.addLayout(chat_layout, 1)

    def on_send_message(self):
        user_request = self.entry_field.text().strip()
        if not user_request:
            return
        
        # === ДОБАВЛЯЕМ В ЧАТ ===
        self.chat_window.append(f"Ты: {user_request}")
        self.mongodb.add_record(
            self.mongodb.phrases,
            {"role": "user", "content": user_request, "timestamp": datetime.now()}
        )
        self.entry_field.clear()

        # === ЛОГ ===
        print(f"\n{'='*60}")
        print(f"📨 НОВЫЙ ЗАПРОС")
        print(f"{'='*60}")
        print(f"📝 '{user_request}'")

        # === ИСТОРИЯ ===
        dialogue_history = self.mongodb.get_n_records(self.mongodb.phrases, 30)
        print(f"📌 История загружена: {len(dialogue_history)} сообщений")


        # === ФАЗА 1: Memory Agent — анализирует, нужно ли искать/сохранять ===
        try:
            planning_memory = self.memory_agent.activate_memory_agent_phase1(user_request, dialogue_history)
            requires_memory = planning_memory.get("requires_memory", False)
            is_new_info = planning_memory.get("is_new_info", False)
        except Exception as e:
            print(f"❌ Ошибка MemoryAgent Phase1: {e}")
            requires_memory = False
            is_new_info = False

        # === ФАЗА 2: Memory Agent — ищет, обновляет, возвращает контекст ===
        relevant_memories = []
        if requires_memory or is_new_info:
            relevant_memories = self.memory_agent.activate_memory_agent_phase2(
                user_request=user_request,
                dialogue_context=dialogue_history,
                first_step_response=planning_memory if isinstance(planning_memory, dict) else {}
            )
        else:
            relevant_memories = []

        # === ФАЗА ОТВЕТА: Один вызов модели ===
        system_prompt = self.build_final_system_prompt(user_request, relevant_memories)
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        for msg in dialogue_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        print(messages)

        print(f"\n🧠 → ЗАПРОС К МОДЕЛИ (ФИНАЛЬНЫЙ ОТВЕТ)")
        try:
            response = self.client.chat_completion(
                model="openai/gpt-oss-20b:free",
                messages=messages,
                schema=AURORA_SCHEMA
            )
        except Exception as e:
            print(f"❌ ОШИБКА API: {e}")
            self.chat_window.append("Аврора: У меня техническая ошибка. Повтори позже.")
            return

        if isinstance(response, str) or "error" in response:
            print(f"❌ ОШИБКА: {response}")
            self.chat_window.append("Аврора: Не могу ответить — ошибка.")
            return

        print(f"\n🔍 ← ОТВЕТ МОДЕЛИ — СЫРОЙ JSON")
        print(json.dumps(response, ensure_ascii=False, indent=2))

        # === ВЫВОД ОТВЕТА ===
        self.render_and_store(response)

    def build_final_system_prompt(self, user_request, relevant_memories):
        # --- Время ---
        last_msg_time = self.get_last_user_message_time()
        time_info = "Ты не помнишь, сколько времени прошло с последнего сообщения."
        if last_msg_time:
            elapsed = datetime.now() - last_msg_time
            hours, rem = divmod(int(elapsed.total_seconds()), 3600)
            minutes = rem // 60
            days = elapsed.days

            if elapsed.total_seconds() < 120:
                time_info = "Андрей только что писал тебе."
            elif hours == 0:
                time_info = f"С последнего сообщения Андрея прошло {minutes} минут."
            elif hours < 24:
                time_info = f"С последнего сообщения Андрея прошло {hours} ч {minutes} мин."
            else:
                time_info = f"С последнего разговора прошло {days} дн."

        time_info += f" Время сейчас: {datetime.now().strftime('%d.%m.%y %H:%M')}."

        # --- Критические границы ---
        critical_prefs = self.chroma_memory.get_critical_memories()
        critical_text = "\n".join([p for p in critical_prefs]) if critical_prefs else "ничего."

        # --- Релевантные воспоминания ---
        memory_text = "\n".join([m["text"] for m in relevant_memories]) if relevant_memories else "ничего."

        # --- Сборка промта ---
        prompt_parts = [
            PERSONALITY_PROMPT,
            FINAL_RESPONSE_PHASE_PROMPT,
            "Критические границы: " + critical_text,
            time_info,
            f"Андрей сказал: {user_request}",
            "Релевантные воспоминания из памяти:",
            memory_text,
            FINAL_EXAMPLES_PROMPT
        ]
        return "\n\n".join(prompt_parts)

    def get_last_user_message_time(self):
        recent = self.mongodb.get_n_records(self.mongodb.phrases, 5)
        for msg in recent:
            if msg.get("role") == "user" and "timestamp" in msg:
                return msg["timestamp"]
        return None

    def set_mood(self, mood: str):
        image_path = MOOD_IMAGES.get(mood.lower(), MOOD_IMAGES["neutral"])
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.aurora_pic.setPixmap(pixmap)

    def render_and_store(self, aurora_answer: dict):
        # Очистка ответа от <think> тегов
        final_answer = re.sub(
            r'<think>.*?</think>', '', aurora_answer.get("final_answer", ""), flags=re.DOTALL
        ).strip() or "…"

        self.audio_manager.generate_speech(final_answer)

        # Вывод в чат
        self.chat_window.append(f"Аврора: {final_answer}")
        
        self.audio_manager.play_speech()
        # Смена настроения
        mood = aurora_answer.get("mood", "neutral")
        self.set_mood(mood)

        # Сохранение в БД
        self.mongodb.add_record(
            self.mongodb.phrases,
            {
                "role": "assistant",
                "content": final_answer,
                "mood": mood,
                "timestamp": datetime.now()
            }
        )
        self.chat_window.ensureCursorVisible()