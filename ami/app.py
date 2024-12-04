from abc import ABC, abstractmethod
from typing import Type, Any
from pydantic import BaseModel, Field, create_model

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
    def _get_raw_response_format(self) -> Type[BaseModel]:
        """Return the app-specific response format without the common fields.
        This is what child classes should implement."""
        pass
    
    @property
    def current_response_format(self) -> Type[BaseModel]:
        """Return the current expected response format, automatically including common fields."""
        raw_format = self._get_raw_response_format()
        
        # Create a new model that includes the thought field and inherits the app-specific fields
        return create_model(
            f"{raw_format.__name__}WithThought",
            thought=(str, Field(description="The agent's reasoning for taking this action")),
            __base__=raw_format
        )
    
    @abstractmethod
    def handle_response(self, response: Any) -> None:
        """Handle a response from the model and update app state accordingly."""
        pass