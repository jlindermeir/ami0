import json
from pydantic import BaseModel, Field
from typing import Optional, Union, Literal

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

class Response(BaseModel):
    timestamp: str
    results: list[CommandResponse]
    browser_results: list[BrowserResponse]

class NavigateAction(BaseModel):
    action: Literal["navigate"] = "navigate"
    target: str = Field(description="URL to navigate to")
    
    model_config = {
        "extra": "forbid"
    }

class ClickAction(BaseModel):
    action: Literal["click"] = "click"
    target: str = Field(description="Element number to click")
    
    model_config = {
        "extra": "forbid"
    }

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
    
    model_config = {
        "extra": "forbid"
    }

# Generate the schema from the model and ensure additionalProperties: false at all levels
base_schema = Request.model_json_schema()

def add_additional_properties_false(schema):
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            schema["additionalProperties"] = False
            if "properties" in schema:
                schema["required"] = list(schema["properties"].keys())
        for value in schema.values():
            add_additional_properties_false(value)
    elif isinstance(schema, list):
        for item in schema:
            add_additional_properties_false(item)
    return schema

base_schema = add_additional_properties_false(base_schema)

request_json_schema = {
    "type": "json_schema",
    "json_schema": {
        "name": "executionRequest",
        "strict": True,
        "schema": base_schema
    }
}
