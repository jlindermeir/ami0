from pydantic import BaseModel, Field

class LaunchAppResponse(BaseModel):
    """Response for launching an app from the home screen."""
    app_name: str = Field(description="Name of the app to launch")

class ExitAppResponse(BaseModel):
    """Response for exiting an app and returning to home screen."""
    pass 