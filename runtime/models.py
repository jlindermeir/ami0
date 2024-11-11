from pydantic import BaseModel

class Request(BaseModel):
    thoughts: list[str]
    commands: list[str]
    websites: list[str]  # Added this field for website URLs

class CommandResponse(BaseModel):
    exit_code: int
    stdout: str
    stderr: str

class WebsiteLink(BaseModel):
    text: str
    link: str

class WebsiteResponse(BaseModel):
    url: str
    content: str
    links: list[WebsiteLink]

class Response(BaseModel):
    timestamp: str
    results: list[CommandResponse]
    website_results: list[WebsiteResponse]  # Added this field for website responses

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
                "websites": {
                    "type": "array",
                    "description": "List of website URLs to load",
                    "items": {
                        "type": "string",
                    }
                }
            },
            "required": [
                "thoughts",
                "commands",
                "websites"
            ],
            "additionalProperties": False
        }
    }
}
