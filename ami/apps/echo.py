from enum import Enum
from typing import Type
from pydantic import BaseModel, Field

from ami.app import App

class TextEffect(str, Enum):
    """Available text effects for the echo app."""
    UPPERCASE = "uppercase"
    LOWERCASE = "lowercase"
    REVERSE = "reverse"
    ALTERNATING = "alternating"

class EchoAction(BaseModel):
    """Action model for the Echo app."""
    message: str = Field(description="The message to echo back")
    effect: TextEffect = Field(description="The text effect to apply")

class EchoApp(App):
    """A simple app that echoes back messages with different text effects."""
    
    def __init__(self, name: str = "echo"):
        super().__init__(name)
    
    @property
    def description(self) -> str:
        return (
            "A fun app that echoes back your messages with different text effects. "
            "Available effects: uppercase, lowercase, reverse, and alternating case."
        )
    
    def _get_raw_response_format(self) -> Type[BaseModel]:
        return EchoAction
    
    def handle_response(self, response: EchoAction) -> str:
        """Apply the selected effect to the message and return it."""
        message = response.message
        effect = response.effect
        
        if effect == TextEffect.UPPERCASE:
            result = message.upper()
        elif effect == TextEffect.LOWERCASE:
            result = message.lower()
        elif effect == TextEffect.REVERSE:
            result = message[::-1]
        elif effect == TextEffect.ALTERNATING:
            result = ''.join(c.upper() if i % 2 == 0 else c.lower()
                           for i, c in enumerate(message))
        
        return f"Echo ({effect.value}): {result}" 