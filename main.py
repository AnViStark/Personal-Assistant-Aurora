from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QSizePolicy
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from dotenv import load_dotenv
import os
import sys

from openrouter_client import OpenRouterClient
from database_handler import DatabaseHandler
from chroma_mem import ChromaHandler
from aurora_window import MainWindow
from memory_agent import MemoryAgent
from chat_tts.chatts import AudioManager


def main():
    load_dotenv("keys.env")
    
    app = QApplication([])

    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY не найден в keys.env")
    
    client = OpenRouterClient(OPENROUTER_API_KEY)
    mongodb = DatabaseHandler()
    chroma_memory = ChromaHandler()
    memory_agent = MemoryAgent(client, chroma_memory)
    audio_manager = AudioManager()

    window = MainWindow(client, mongodb, chroma_memory, memory_agent, audio_manager)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()