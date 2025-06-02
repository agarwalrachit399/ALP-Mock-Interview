import tkinter as tk
from tkinter import scrolledtext
from threading import Thread

from stt_handler import transcribe_speech
from mock_llm import generate_response  # Replace with your actual module
# from tts_handler import speak_response  # Ready for future integration

class InterviewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Amazon Mock Interview Assistant")

        self.start_button = tk.Button(root, text="🎤 Start Speaking", command=self.start_transcription_thread)
        self.start_button.pack(pady=10)

        self.transcript_label = tk.Label(root, text="You Said:")
        self.transcript_label.pack()

        self.transcript_box = scrolledtext.ScrolledText(root, width=60, height=5, wrap=tk.WORD)
        self.transcript_box.pack(padx=10, pady=5)

        self.response_label = tk.Label(root, text="Bot's Response:")
        self.response_label.pack()

        self.response_box = scrolledtext.ScrolledText(root, width=60, height=5, wrap=tk.WORD)
        self.response_box.pack(padx=10, pady=5)

    def start_transcription_thread(self):
        self.start_button.config(state=tk.DISABLED)
        thread = Thread(target=self.handle_transcription_and_response)
        thread.start()

    def handle_transcription_and_response(self):
        self.transcript_box.delete("1.0", tk.END)
        self.response_box.delete("1.0", tk.END)

        # Step 1: Get transcript
        user_text = transcribe_speech()

        # Step 2: Display user transcript
        self.transcript_box.insert(tk.END, user_text)

        # Step 3: Generate bot response
        bot_response = generate_response(user_text)
        self.response_box.insert(tk.END, bot_response)

        # Step 4 (future): speak_response(bot_response)

        self.start_button.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = InterviewApp(root)
    root.mainloop()
