from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel, QMainWindow, QSizePolicy
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
import subprocess
import re
from datetime import datetime


from prompts import (
    PERSONALITY_PROMPT,
    MEMORY_PROMPT,
    TOOLS_PROMPT,
    EXAMPLES_PROMPT,
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
        
        self.chat_window.append(f"Ты: {self.user_request}")
        self.mongodb.add_record(
            self.mongodb.phrases, 
            {
                "role": "user",
                "content": self.user_request,
                "timestamp": datetime.now()
            }
        )
        self.entry_field.clear()

        # Формируем промпт
        system_prompt = self.build_system_prompt(self.user_request)

        # Получаем историю диалога
        dialogue_history = self.mongodb.get_n_records(self.mongodb.phrases, 30)
        messages = [{"role": "system", "content": system_prompt}]
        for msg in reversed(dialogue_history):
            safe_msg = {
            "role": msg["role"],
            "content": msg["content"]
            }
            messages.append(safe_msg)
        
        # Запрос к ИИ
        aurora_answer = self.client.chat_completion(
            model="deepseek/deepseek-chat-v3-0324:free",
            messages=messages
        )

        # Проверка: что вернул клиент?
        if isinstance(aurora_answer, str):
            print(f"❌ Ошибка от API: {aurora_answer}")
            self.chat_window.append("Аврора: Ой, что-то пошло не так... Не могу ответить.")
            return

        # Обработка ответа
        cleaned_final_answer = re.sub(r'<think>.*?</think>', '', aurora_answer["final_answer"], flags=re.DOTALL).strip()
        self.chat_window.append(f"Аврора: {cleaned_final_answer}")

        # Эмоция
        mood = aurora_answer.get("mood", "neutral")
        self.set_mood(mood)

        # Инструменты
        tool = aurora_answer.get("tool")
        if tool and tool != "none":
            self.execute_tool(tool, aurora_answer.get("tool_arguments", {}))

        # Сохранение предпочтений
        if aurora_answer.get("add_user_preference"):
            self.add_user_preference(aurora_answer["add_user_preference"])

        record_data = {
            "role": "assistant",
            "content": cleaned_final_answer,
            "mood": mood
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

        try:
            self.chroma_memory.add_record(
                text=preference_text,
                category=category,
                importance=importance
            )
            print(f"✅ Сохранено в Chroma: {preference_text}")
        except Exception as e:
            print(f"❌ Ошибка при сохранении в Chroma: {e}")
        
        try:
            self.mongodb.add_record(
                self.mongodb.user_preferences,
                {
                    "text": preference_text,
                    "category": category,
                    "importance": importance
                }
            )
        except Exception as e:
            print(f"❌ Ошибка при сохранении в MongoDB: {e}")

    def build_system_prompt(self, user_request):
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

        time_info += f"Время сейчас: {datetime.now().strftime('%d.%m.%y %H:%M')}"

        critical_prefs = self.chroma_memory.get_critical_memories()
        context_prefs = self.chroma_memory.search_memory(user_request, 4)

        prompt_parts = [
            PERSONALITY_PROMPT,
            time_info,
            "На данный момент тебе известно о следующих предпочтениях критического уровня:",
            "\n".join(map(str, critical_prefs)) if critical_prefs else "ничего.",
            "Также в твоей памяти под последнюю фразу Андрея ты нашла следующие воспоминания:",
            "\n".join(map(str, context_prefs)) if context_prefs else "ничего.",
            MEMORY_PROMPT,
            TOOLS_PROMPT,
            EXAMPLES_PROMPT
        ]   
        print(time_info)
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

    def open_app(self, name: str):
        cmd = APP_MAPPING.get(name.lower())
        if cmd:
            subprocess.Popen(cmd, shell=(name == "windows_settings"))