from abc import ABC, abstractmethod
from typing import Type, List, Tuple, Optional
from pydantic import BaseModel

class App(ABC):
    """Base class for all apps in the system."""
    
    def __init__(self, name: str):
        self.name = name
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return a brief description of the app for the home screen."""
        pass
    
    @property
    @abstractmethod
    def usage_prompt(self) -> str:
        """Return a detailed prompt explaining how to use the app.
        This can be dynamic based on the app's current state."""
        pass
    
    @abstractmethod
    def get_action_models(self) -> List[Type[BaseModel]]:
        """Return a list of all possible action models this app supports."""
        pass
    
    @abstractmethod
    def handle_response(self, response: BaseModel) -> Tuple[str, Optional[str]]:
        """Handle a response from the model and update app state accordingly.
        Returns a tuple of (text_response, optional_base64_image)."""
        pass