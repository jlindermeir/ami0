from enum import Enum
from typing import List, Literal
from pydantic import BaseModel, Field

class BaseResponse(BaseModel):
    """Base response model that all responses must include."""
    thoughts: List[str] = Field(description="The agent's thoughts and reasoning process")

class LaunchAppAction(BaseModel):
    """Action for launching an app from the home screen."""
    type: Literal["launch_app"]
    # Note: app_name field will be added dynamically by the OS

class ExitAppAction(BaseModel):
    """Action for exiting the current app."""
    type: Literal["exit_app"]
 