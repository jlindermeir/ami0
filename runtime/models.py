from pydantic import BaseModel, Field
from typing import Optional, Union, Literal

class CommandResponse(BaseModel):
    exit_code: int
    stdout: str
    stderr: str

class BrowserResponse(BaseModel):
    url: str
    content: str

class Response(BaseModel):
    timestamp: str
    results: list[CommandResponse]
    browser_result: Optional[BrowserResponse] = None

class NavigateAction(BaseModel):
    action: Literal["navigate"] = "navigate"
    target: str = Field(description="URL to navigate to")

class ClickAction(BaseModel):
    action: Literal["click"] = "click"
    target: str = Field(description="Element number to click")

class Request(BaseModel):
    thoughts: list[str] = Field(
        description="List of the assistant's thoughts related to the task"
    )
    commands: list[str] = Field(
        description="List of commands to execute on the server via SSH"
    )
    browser_action: Optional[Union[NavigateAction, ClickAction]] = Field(
        description="Single browser action to perform (navigate or click) or null if none"
    )
