from pydantic import BaseModel

class CommandResponse(BaseModel):
    exit_code: int
    stdout: str
    stderr: str

class BrowserOption(BaseModel):
    number: int
    text: str
    href: str

class BrowserResponse(BaseModel):
    url: str
    content: str
    options: list[BrowserOption]

class Response(BaseModel):
    timestamp: str
    results: list[CommandResponse]
    browser_results: list[BrowserResponse]

class BrowserAction(BaseModel):
    action: str  # e.g., "navigate", "click"
    target: str  # URL for "navigate", element number for "click"

class Request(BaseModel):
    thoughts: list[str]
    commands: list[str]
    browser_actions: list[BrowserAction]

request_json_schema = {
    "type": "json_schema",
    "json_schema": {
        "name": "executionRequest",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "thoughts": {
                    "type": "array",
                    "description": "List of the assistant's thoughts related to the task",
                    "items": {
                        "type": "string"
                    }
                },
                "commands": {
                    "type": "array",
                    "description": "List of commands to execute on the server via SSH",
                    "items": {
                        "type": "string"
                    }
                },
                "browser_actions": {
                    "type": "array",
                    "description": "List of browser actions to perform",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "The browser action to perform, e.g., 'navigate', 'click'"
                            },
                            "target": {
                                "type": "string",
                                "description": "The target of the action, e.g., URL for 'navigate', element number for 'click'"
                            }
                        },
                        "required": ["action", "target"],
                        "additionalProperties": False
                    }
                }
            },
            "required": [
                "thoughts",
                "commands",
                "browser_actions"
            ],
            "additionalProperties": False
        }
    }
}
