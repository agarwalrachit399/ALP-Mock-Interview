from abc import ABC, abstractmethod
from typing import Generator

class BaseLLMClient(ABC):
    @abstractmethod
    # def generate_stream(self, prompt: str) -> Generator[str, None, None]:
    def generate_stream(self, prompt: str) -> str:
        pass

    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass