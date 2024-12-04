from enum import Enum
from pydantic import BaseModel, Field

class LaunchAppResponse(BaseModel):
    """Response for launching an app from the home screen."""
    # Note: app_name field will be replaced dynamically by the OS
    pass

class ExitAppResponse(BaseModel):
    """Response for exiting an app and returning to home screen."""
    pass 