from enum import Enum
from typing import Type, List, Tuple, Optional, Literal
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
    type: Literal["echo"]
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
    
    @property
    def usage_prompt(self) -> str:
        return f"""
This is the Echo app. You can send messages and have them echoed back with different text effects.

Available effects:
- {TextEffect.UPPERCASE.value}: Converts text to UPPERCASE
- {TextEffect.LOWERCASE.value}: Converts text to lowercase
- {TextEffect.REVERSE.value}: Reverses the text
- {TextEffect.ALTERNATING.value}: AlTeRnAtEs between upper and lower case

Example action:
{{
    "type": "echo",
    "message": "Hello World",
    "effect": "uppercase"
}}

This would return: "HELLO WORLD"
""".strip()
    
    def get_action_models(self) -> List[Type[BaseModel]]:
        """Return the action models supported by this app."""
        return [EchoAction]
    
    def handle_response(self, response: EchoAction) -> Tuple[str, Optional[str]]:
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
        
        return (f"Echo ({effect.value}): {result}", None) 