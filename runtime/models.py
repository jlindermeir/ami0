from pydantic import BaseModel


class Request(BaseModel):
    thoughts: list[str]
    commands: list[str]


class CommandResponse(BaseModel):
    exit_code: int
    stdout: str
    stderr: str


class Response(BaseModel):
    timestamp: str
    results: list[CommandResponse]


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
                }
            },
            "required": [
                "thoughts",
                "commands"
            ],
            "additionalProperties": False
        }
    }
}
