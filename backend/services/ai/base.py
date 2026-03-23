from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GradingResult:
    score: float
    suggestion: str


class BaseAIAdapter(ABC):
    def __init__(self, api_key: str, base_url: str, model_name: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name

    @abstractmethod
    def grade(self, content: str, criteria: str) -> GradingResult:
        ...
