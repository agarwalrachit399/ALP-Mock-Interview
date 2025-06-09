from abc import ABC, abstractmethod

class LLMClientBase(ABC):
    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.3) -> str:
        pass
