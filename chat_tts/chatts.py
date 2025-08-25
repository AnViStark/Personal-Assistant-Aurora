import torchaudio as ta
from chatterbox.tts import ChatterboxTTS
import simpleaudio as sa

class AudioManager():
    def __init__(self):
        self.model = ChatterboxTTS.from_pretrained(device="cuda")
        self.audio_prompt_path = "chat_tts\\shadow.wav"
    
    def generate_speech(self, text):
        wav = self.model.generate(text, audio_prompt_path=self.audio_prompt_path, exaggeration=0.5, cfg_weight=0.5)
        ta.save("chat_tts\\speech.wav", wav, self.model.sr, encoding='PCM_S', bits_per_sample=16)

    def play_speech(self, audio_file = "chat_tts\\speech.wav"):
        wave_obj = sa.WaveObject.from_wave_file(audio_file)
        play_obj = wave_obj.play()

        play_obj.wait_done()

if __name__ == "__main__":
    manager = AudioManager()
    manager.generate_speech("I can feel the warmth of the morning sun spilling through the window, brushing against my skin like a gentle caress. There’s a soft hum in the air, the kind that makes your heart ache with a mixture of longing and hope. Somewhere in the distance, birds are calling to each other, their voices weaving together in a delicate symphony that feels almost alive. I take a deep breath, tasting the faint scent of blooming flowers mixed with the crisp freshness of early dew.")
    manager.play_speech()
