from pydantic import BaseModel, Field
from typing import Optional, Union, Literal

class CommandResponse(BaseModel):
    exit_code: int
    stdout: str
    stderr: str

class BrowserResponse(BaseModel):
    url: str
    content: str
    has_screenshot: bool = False

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

class ScreenshotAction(BaseModel):
    action: Literal["screenshot"] = "screenshot"

class Recommendation(BaseModel):
    position: Literal["yes", "no"] = Field(description="Whether to buy 'yes' or 'no' shares")
    justifications: list[str] = Field(description="List of reasons supporting this position")
    confidence: float = Field(description="Confidence level, in percentage")

class Request(BaseModel):
    thoughts: list[str] = Field(
        description="List of the assistant's thoughts related to the task"
    )
    commands: list[str] = Field(
        description="List of commands to execute on the server via SSH"
    )
    browser_action: Optional[Union[NavigateAction, ClickAction, ScreenshotAction]] = None
    recommendation: Optional[Recommendation] = Field(
        description="Final market position recommendation. When set, this signals task completion.",
        default=None
    )
