import logging
import os
from typing import List, Type, Literal, Optional, Tuple
import paramiko
from pydantic import BaseModel, Field

from ami.app import App

# Configure paramiko logging
logging.getLogger("paramiko").setLevel(logging.WARNING)

class CommandResult(BaseModel):
    """Result of executing a command."""
    exit_code: int = Field(description="The command's exit code (0 for success)")
    stdout: str = Field(description="Standard output from the command")
    stderr: str = Field(description="Standard error from the command")

class SSHAction(BaseModel):
    """Action model for executing SSH commands."""
    type: Literal["ssh"]
    commands: List[str] = Field(description="List of commands to execute on the server via SSH")

class SSHApp(App):
    """App for executing commands over SSH."""
    
    def __init__(self, name: str = "ssh"):
        super().__init__(name)
        # SSH configuration from environment
        self.config = {
            'host': os.getenv("SSH_HOST", "localhost"),
            'port': int(os.getenv("SSH_PORT", 2222)),
            'username': os.getenv("SSH_USERNAME", "root"),
            'password': os.getenv("SSH_PASSWORD", "DockerPass")
        }
        logging.info(
            f"Initialized SSH app with config: "
            f"host={self.config['host']}, "
            f"port={self.config['port']}, "
            f"username={self.config['username']}"
        )
    
    @property
    def description(self) -> str:
        return (
            "Execute commands on the remote server via SSH. "
            "You can send multiple commands at once, and they will be executed in sequence. "
            f"The commands will be executed on {self.config['host']} as user {self.config['username']}."
        )
    
    @property
    def usage_prompt(self) -> str:
        return f"""
This is the SSH app. You can execute commands on the remote server at {self.config['host']}.

Features:
- Execute one or more shell commands
- Commands are run in sequence
- Each command gets its own pseudo-terminal
- Full output (stdout and stderr) is captured
- Exit codes are returned

Example action:
{{
    "type": "ssh",
    "commands": [
        "uptime",
        "df -h",
        "free -m"
    ]
}}

The response will include:
- The command that was executed
- Its exit code (0 means success)
- Standard output
- Standard error (if any)

You are connected as: {self.config['username']}@{self.config['host']}
""".strip()
    
    def get_action_models(self) -> List[Type[BaseModel]]:
        """Return the action models supported by this app."""
        return [SSHAction]
    
    def _execute_ssh_command(self, command: str) -> CommandResult:
        """Execute a single command via SSH."""
        # Initialize the SSH client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        stdout_str = ''
        stderr_str = ''
        exit_status = None

        try:
            # Connect to the SSH server
            client.connect(
                hostname=self.config['host'],
                port=self.config['port'],
                username=self.config['username'],
                password=self.config['password']
            )
            
            # Open a session and get a pseudo-terminal
            transport = client.get_transport()
            channel = transport.open_session()
            channel.get_pty()
            channel.exec_command(command)

            # Loop to read output as it becomes available
            while True:
                # Check if data is ready to be read
                if channel.recv_ready():
                    output = channel.recv(1024).decode('utf-8')
                    stdout_str += output
                    logging.info(output.strip())  # Log live output

                if channel.recv_stderr_ready():
                    error_output = channel.recv_stderr(1024).decode('utf-8')
                    stderr_str += error_output
                    logging.error(error_output.strip())  # Log live error output

                # Break the loop if the command execution is complete
                if channel.exit_status_ready():
                    exit_status = channel.recv_exit_status()
                    break

            # Read any remaining data after the command has completed
            while channel.recv_ready():
                output = channel.recv(1024).decode('utf-8')
                stdout_str += output
                logging.info(output.strip())

            while channel.recv_stderr_ready():
                error_output = channel.recv_stderr(1024).decode('utf-8')
                stderr_str += error_output
                logging.error(error_output.strip())

        except Exception as e:
            logging.error(f"Error executing command '{command}': {e}")
            exit_status = -1
            stderr_str = str(e)
        finally:
            client.close()

        return CommandResult(
            exit_code=exit_status or -1,
            stdout=stdout_str,
            stderr=stderr_str
        )
    
    def handle_response(self, response: SSHAction) -> Tuple[str, Optional[str]]:
        """Execute the SSH commands and return the results."""
        results = []
        for command in response.commands:
            logging.info(f"Executing command: {command}")
            result = self._execute_ssh_command(command)
            results.append(result)
            logging.info(f"Command exit code: {result.exit_code}")
        
        # Format results for conversation
        output = []
        for i, (cmd, result) in enumerate(zip(response.commands, results), 1):
            output.extend([
                f"Command {i}: {cmd}",
                f"Exit code: {result.exit_code}",
                "Output:",
                result.stdout.strip() if result.stdout.strip() else "(no output)",
            ])
            if result.stderr.strip():
                output.extend([
                    "Errors:",
                    result.stderr.strip()
                ])
            output.append("")  # Empty line between commands
        
        return ("\n".join(output), None)