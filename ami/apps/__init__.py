"""
AMI Apps Package - Collection of applications that can be used by the agent.
"""

from .echo import EchoApp
from .ssh import SSHApp

__all__ = ['EchoApp', 'SSHApp']
