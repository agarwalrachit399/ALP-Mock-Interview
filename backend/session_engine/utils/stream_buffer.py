import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import re

class StreamTextChunkBuffer:
    def __init__(self, tts):
        self.tts = tts
        self.buffer = ""

    def feed_chunk(self, chunk):
        if not chunk.strip():
            return

        self.buffer += chunk

        # Check if buffer contains any sentence-ending punctuation
        match = re.search(r'[.!?]', self.buffer)
        if match:
            end_idx = match.end()  # include the punctuation
            to_speak = self.buffer[:end_idx]
            self.tts.speak(to_speak)
            self.buffer = self.buffer[end_idx:]  # Keep remaining part

    def flush(self):
        """Speak any remaining text at the end of the stream."""
        if self.buffer.strip():
            self.tts.speak(self.buffer)
            self.buffer = ""
