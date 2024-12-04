from abc import ABC, abstractmethod
from typing import Type, List
from pydantic import BaseModel

class App(ABC):
    """Base class for all apps in the system."""
    
    def __init__(self, name: str):
        self.name = name
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return a description of the app for the system prompt."""
        pass
    
    @abstractmethod
    def get_action_models(self) -> List[Type[BaseModel]]:
        """Return a list of all possible action models this app supports."""
        pass
    
    @abstractmethod
    def handle_response(self, response: BaseModel) -> str:
        """Handle a response from the model and update app state accordingly."""
        pass