"""
AMI Apps Package - Collection of applications that can be used by the agent.
"""

from .echo import EchoApp
from .ssh import SSHApp
from .browser import BrowserApp

__all__ = ['EchoApp', 'SSHApp', 'BrowserApp']
