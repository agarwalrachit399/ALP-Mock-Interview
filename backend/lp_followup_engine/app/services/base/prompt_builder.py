from abc import ABC, abstractmethod

class PromptBuilder(ABC):
    @abstractmethod
    def build(self, **kwargs) -> str:
        pass