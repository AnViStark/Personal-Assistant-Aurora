from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel, QMainWindow, QSizePolicy
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
import subprocess
import re
from datetime import datetime
import json


from prompts import (
    PERSONALITY_PROMPT,
    PLANNING_PHASE_PROMPT,
    MEMORY_PROMPT,
    TOOLS_PROMPT,
    PLANNING_EXAMPLES_PROMPT,
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

APP_MAPPING = {
    "calculator": "calc.exe",
    "cmd": ["cmd.exe", "/c", "start", "cmd.exe"],
    "windows_settings": ["start", "ms-settings:"],
    "notepad": "notepad.exe",
}

class MainWindow(QMainWindow):
    def __init__(self, client, mongodb, chroma_memory):
        super().__init__()
        
        self.client = client
        self.mongodb = mongodb
        self.chroma_memory = chroma_memory

        self.setWindowTitle("Аврора")
        self.resize(850, 700)

        self.setup_ui()
        self.set_mood("neutral")

    def setup_ui(self):
        # 1. Создаём центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 2. Теперь можно создать layout и установить его на central_widget
        main_layout = QHBoxLayout(central_widget)

        # Левая часть — картинка
        self.aurora_pic = QLabel()
        self.aurora_pic.setAlignment(Qt.AlignCenter)
        self.aurora_pic.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.aurora_pic.setMinimumSize(200, 200)
        self.aurora_pic.setScaledContents(True)

        # Правая часть — чат
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

        # Добавляем виджеты в основной layout
        main_layout.addWidget(self.aurora_pic, 1)  # картинка слева
        main_layout.addLayout(chat_layout, 1)     # чат справа

    def on_send_message(self):
        self.user_request = self.entry_field.text().strip()
        if not self.user_request:
            return

        # === ЛОГ: Новый запрос ===
        print(f"\n{'='*60}")
        print(f"📨 НОВЫЙ ЗАПРОС")
        print(f"{'='*60}")
        print(f"📝 '{self.user_request}'")

        self.chat_window.append(f"Ты: {self.user_request}")
        self.mongodb.add_record(
            self.mongodb.phrases,
            {"role": "user", "content": self.user_request, "timestamp": datetime.now()}
        )
        self.entry_field.clear()

        # === Загрузка истории ===
        dialogue_history = self.mongodb.get_n_records(self.mongodb.phrases, 30)
        print(f"\n📌 История загружена: {len(dialogue_history)} сообщений")

        # === ФАЗА 1: ПЛАНИРОВАНИЕ ===
        planning_system_prompt = self.build_planning_system_prompt(self.user_request)
        messages = [{"role": "system", "content": planning_system_prompt}]
        for msg in reversed(dialogue_history):
            messages.append({"role": msg["role"], "content": msg["content"]})

        print(f"\n🧠 → ЗАПРОС К МОДЕЛИ (ФАЗА 1)")
        planning_answer = self.client.chat_completion(
            model="deepseek/deepseek-chat-v3-0324:free",
            messages=messages
        )

        if isinstance(planning_answer, str):
            print(f"❌ ОШИБКА API: {planning_answer}")
            self.chat_window.append("Аврора: У меня сбой. Попробуй ещё раз.")
            return

        # === Вывод сырого ответа фазы 1 ===
        print(f"\n🔍 ← ОТВЕТ МОДЕЛИ (ФАЗА 1) — СЫРОЙ JSON")
        print(json.dumps(planning_answer, ensure_ascii=False, indent=2))

        # Сохранение предпочтения (только один раз + лог)
        if planning_answer.get("add_user_preference"):
            print(f"💾 СОХРАНЯЮ ПРЕДПОЧТЕНИЕ: {planning_answer['add_user_preference']['preference']}")
            self.add_user_preference(planning_answer["add_user_preference"])

        # Если ответ готов — выводим
        if not planning_answer.get("requires_follow_up"):
            print(f"🟢 ФАЗА 1: ответ готов, второй вызов не нужен")
            self.render_and_store(planning_answer)
            return

        # === ФАЗА 2: ФИНАЛЬНЫЙ ОТВЕТ ===
        print(f"\n🔄 ПЕРЕХОД К ФАЗЕ 2")
        final_system_prompt = self.build_final_system_prompt(
            self.user_request,
            planning_answer.get("requires_tool_result"),
            planning_answer.get("tool"),
            planning_answer.get("tool_arguments"),
            planning_answer.get("memory_query"),
            planning_answer.get("requires_memory"),
            planning_answer.get("thoughts"),
        )

        messages = [{"role": "system", "content": final_system_prompt}]
        for msg in reversed(dialogue_history):
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({
            "role": "assistant",
            "content": json.dumps(planning_answer, ensure_ascii=False)
        })

        print(f"\n🧠 → ЗАПРОС К МОДЕЛИ (ФАЗА 2)")
        final_answer = self.client.chat_completion(
            model="deepseek/deepseek-chat-v3-0324:free",
            messages=messages
        )

        if isinstance(final_answer, str):
            print(f"❌ ОШИБКА API (фаза 2): {final_answer}")
            self.chat_window.append("Аврора: Ошибка при генерации ответа.")
            return

        # === Вывод сырого ответа фазы 2 ===
        print(f"\n🔍 ← ОТВЕТ МОДЕЛИ (ФАЗА 2) — СЫРОЙ JSON")
        print(json.dumps(final_answer, ensure_ascii=False, indent=2))

        # Сохранение предпочтения (если есть)
        if final_answer.get("add_user_preference"):
            print("⚠️  Предпочтение уже сохранено в первой фазе, пропускаю вторую.")

        # Вывод в интерфейс
        print(f"📤 ВЫВОЖУ ОТВЕТ В ЧАТ")
        self.render_and_store(final_answer)

    def render_and_store(self, aurora_answer: dict):
        cleaned_final_answer = re.sub(
            r'<think>.*?</think>', '', aurora_answer.get("final_answer", ""), flags=re.DOTALL
        ).strip() or "[пусто]"

        self.chat_window.append(f"Аврора: {cleaned_final_answer}")

        mood = aurora_answer.get("mood", "neutral")
        self.set_mood(mood)

        tool = aurora_answer.get("tool")
        if tool and tool != "none":
            self.execute_tool(tool, aurora_answer.get("tool_arguments", {}))

        record_data = {
            "role": "assistant",
            "content": cleaned_final_answer,
            "mood": mood,
            "timestamp": datetime.now()
        }
        if "add_user_preference" in aurora_answer:
            record_data["add_user_preference"] = aurora_answer["add_user_preference"]

        self.mongodb.add_record(self.mongodb.phrases, record_data)
        self.chat_window.ensureCursorVisible()

    def add_user_preference(self, pref):
        if not pref:
            print("Нет данных для сохранения предпочтения")
            return
        
        preference_text = pref.get("preference")
        category = pref.get("category")
        importance = pref.get("importance")

        if not preference_text or not category or not importance:
            print("❌ Недостаточно данных для сохранения предпочтения")
            return

        # 1. Пытаемся добавить в Chroma → он сам проверит дубликат
        success = self.chroma_memory.add_record(
            text=preference_text,
            category=category,
            importance=importance
        )

        # 2. Только если успешно добавлено в Chroma — добавляем в MongoDB
        if success is not False:  # add_record возвращает None при успехе, False при дубликате
            try:
                self.mongodb.add_record(
                    self.mongodb.user_preferences,
                    {
                        "text": preference_text,
                        "category": category,
                        "importance": importance,
                        "timestamp": datetime.now()
                    }
                )
                print(f"✅ Сохранено в MongoDB: {preference_text}")
            except Exception as e:
                print(f"❌ Ошибка при сохранении в MongoDB: {e}")
        else:
            print(f"🚫 Пропускаю MongoDB: дубликат не добавляется — {preference_text}")

    def build_planning_system_prompt(self, user_request):
        last_user_message_time = self.get_last_user_message_time()
        time_info = "Ты не помнишь, сколько времени прошло с последнего сообщения."
        if last_user_message_time:
            elapsed = datetime.now() - last_user_message_time
            hours, rem = divmod(int(elapsed.total_seconds()), 3600)
            minutes = rem // 60
        
        if elapsed.total_seconds() < 120:
            time_info = "Андрей только что писал тебе."
        elif hours == 0:
            time_info = f"С последнего сообщения Андрея прошло {minutes} минут."
        elif hours < 24:
            time_info = f"С последнего сообщения Андрея прошло {hours} ч {minutes} мин."
        else:
            time_info = f"С последнего разговора прошло {elapsed.days} дн."

        time_info += f"Время сейчас: {datetime.now().strftime('%d.%m.%y %H:%M')}. Ссылайся на данные о времени (время сейчас и время последнего сообщения от пользователя), если это уместно в текущей ситуации (например можешь посоветовать идти спать, если уже поздно, или пожелать доброго утра)."

        critical_prefs = self.chroma_memory.get_critical_memories()
        # context_prefs = self.chroma_memory.search_memory(user_request, 4)

        prompt_parts = [
            PERSONALITY_PROMPT,
            PLANNING_PHASE_PROMPT,
            time_info,
            "На данный момент тебе известно о следующих предпочтениях критического уровня:",
            "\n".join(map(str, critical_prefs)) if critical_prefs else "ничего.",
            # "Также в твоей памяти под последнюю фразу Андрея ты нашла следующие воспоминания:",
            # "\n".join(map(str, context_prefs)) if context_prefs else "ничего.",
            MEMORY_PROMPT,
            TOOLS_PROMPT,
            PLANNING_EXAMPLES_PROMPT
        ]
        print(time_info)
        # print("\n\n".join(prompt_parts))
        return "\n\n".join(prompt_parts)
    
    def build_final_system_prompt(self, user_request, requires_tool_result, tool, tool_arguments, memory_query, requires_memory, thoughts):
        last_user_message_time = self.get_last_user_message_time()
        if last_user_message_time:
            elapsed = datetime.now() - last_user_message_time
            hours, rem = divmod(int(elapsed.total_seconds()), 3600)
            minutes = rem // 60

            if elapsed.total_seconds() < 120:
                time_info = "Андрей только что писал тебе."
            elif hours == 0:
                time_info = f"С последнего сообщения Андрея прошло {minutes} минут."
            elif hours < 24:
                time_info = f"С последнего сообщения Андрея прошло {hours} ч {minutes} мин."
            else:
                time_info = f"С последнего разговора прошло {elapsed.days} дн."
        else:
            time_info = "Ты не помнишь, сколько времени прошло с последнего сообщения."

        time_info += f"Время сейчас: {datetime.now().strftime('%d.%m.%y %H:%M')}. Ссылайся на данные о времени (время сейчас и время последнего сообщения от пользователя), если это уместно в текущей ситуации (например можешь посоветовать идти спать, если уже поздно, или пожелать доброго утра)."

        critical_prefs = self.chroma_memory.get_critical_memories()

        prompt_parts = [
            PERSONALITY_PROMPT,
            time_info,
            "На данный момент тебе известно о следующих предпочтениях критического уровня:",
            "\n".join(map(str, critical_prefs)) if critical_prefs else "ничего.",
            FINAL_RESPONSE_PHASE_PROMPT,
            f"Андрей сказал: {user_request}.",
            f"Твои рассуждения на первой фазе: '{thoughts}'",
            f"НОВАЯ ИНФОРМАЦИЯ:"
        ]

        if requires_memory:
            context_prefs = self.chroma_memory.search_memory(memory_query, 10)
            prompt_parts.append(
                "Семантический поиск по фразе пользователя нашел следующие воспоминания в памяти Авроры, которые могут быть релевантны к текущему запросу:\n" +
                "\n".join(map(str, context_prefs)) if context_prefs else "ничего."
            )
        if requires_tool_result:
            result = self.execute_tool(tool, tool_arguments)
            prompt_parts.append(f"\nРезультат выполнения: инструмента {tool}: {result}")
        
        prompt_parts.extend([
            FINAL_EXAMPLES_PROMPT
        ])

        # print("\n\n".join(prompt_parts))

        return "\n\n".join(prompt_parts)
    
    def get_last_user_message_time(self):
        recent_messages = self.mongodb.get_n_records(self.mongodb.phrases, 5)
        
        for msg in recent_messages:
            if msg.get("role") == "user" and "timestamp" in msg:
                return msg["timestamp"]
        
        return None
    
    def set_mood(self, mood: str):
        image_path = MOOD_IMAGES.get(mood.lower(), MOOD_IMAGES["neutral"])
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.aurora_pic.setPixmap(pixmap)
    
    def execute_tool(self, tool: str, args):
        if tool == "open_app":
            app_name = args.get("app_name")
            if app_name:
                self.open_app(app_name)
                return f"Приложение {app_name} открылось!"

    def open_app(self, name: str):
        cmd = APP_MAPPING.get(name.lower())
        if cmd:
            subprocess.Popen(cmd, shell=(name == "windows_settings"))