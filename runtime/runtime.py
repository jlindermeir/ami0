import datetime
import json
import os
import pathlib

import paramiko
from openai import OpenAI

from runtime.models import CommandResponse, Request, Response, request_json_schema


# Read the system prompt
system_prompt_file_path = pathlib.Path(__file__).parent / "prompts" / "system.md"
with open(system_prompt_file_path, "r") as f:
    system_prompt = f.read()

def execute_ssh_command(host, port, username, password, command):
    # Initialize the SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    stdout_str = ''
    stderr_str = ''
    exit_status = None

    try:
        # Connect to the SSH server
        client.connect(hostname=host, port=port, username=username, password=password)
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
                print(output, end='')  # Print live output

            if channel.recv_stderr_ready():
                error_output = channel.recv_stderr(1024).decode('utf-8')
                stderr_str += error_output
                print(error_output, end='')  # Print live error output

            # Break the loop if the command execution is complete
            if channel.exit_status_ready():
                exit_status = channel.recv_exit_status()
                break

        # Read any remaining data after the command has completed
        while channel.recv_ready():
            output = channel.recv(1024).decode('utf-8')
            stdout_str += output
            print(output, end='')

        while channel.recv_stderr_ready():
            error_output = channel.recv_stderr(1024).decode('utf-8')
            stderr_str += error_output
            print(error_output, end='')

    except Exception as e:
        print(f"Error executing command {command}: {e}")
        exit_status = -1
        stderr_str = str(e)
    finally:
        client.close()

    # Create a CommandResponse object with the collected data
    cmd_response = CommandResponse(
        exit_code=exit_status,
        stdout=stdout_str,
        stderr=stderr_str
    )
    return cmd_response


def main():
    # SSH configuration
    ssh_host = os.getenv("SSH_HOST", "localhost")
    ssh_port = int(os.getenv("SSH_PORT", 2222))
    ssh_username = os.getenv("SSH_USERNAME", "root")
    ssh_password = os.getenv("SSH_PASSWORD", "DockerPass")

    # Conversation history
    conversation = []

    # Initial system prompt
    conversation.append({"role": "system", "content": system_prompt})

    # Initial user message to start the conversation
    user_message = "Please provide the next set of commands."
    conversation.append({"role": "user", "content": user_message})

    # Initialize OpenAI client
    oai_client = OpenAI()

    while True:
        # Send the conversation to the model
        response = oai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation,
            temperature=1,
            max_tokens=2048,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            response_format=request_json_schema
        )

        # Get the assistant's reply
        assistant_reply = response.choices[0].message.content

        # Append assistant's reply to conversation
        conversation.append({"role": "assistant", "content": assistant_reply})

        # Parse assistant_reply into Request object
        try:
            # Remove code blocks if any
            if assistant_reply.startswith("```"):
                assistant_reply = assistant_reply.strip("```")
            # Parse JSON
            assistant_reply_json = json.loads(assistant_reply)
            request = Request(**assistant_reply_json)
        except Exception as e:
            print("Error parsing assistant's reply into Request object:", e)
            print("Assistant's reply was:", assistant_reply)
            # Handle error, perhaps send an error message to assistant
            error_message = f"Error parsing your response: {e}. Please make sure to respond in the correct JSON format."
            conversation.append({"role": "user", "content": error_message})
            continue

        # Output the thoughts to console
        print("Assistant's thoughts:")
        for thought in request.thoughts:
            print(thought)

        # For each command in commands list, send via SSH
        results = []
        for command in request.commands:
            # Prompt the user for confimation if the command should be executed.
            user_input = input(f"Execute command '{command}'? (y/n): ")

            if user_input.lower() != "y":
                print(f"Skipping command '{command}'")
                results.append(CommandResponse(exit_code=-1, stdout="", stderr="Command skipped by user"))
                continue

            # Execute the command via SSH
            print(f"Executing command '{command}' via SSH...")
            cmd_result = execute_ssh_command(ssh_host, ssh_port, ssh_username, ssh_password, command)

            print(f"Exit code: {cmd_result.exit_code}")
            print("STDOUT:")
            print(cmd_result.stdout)
            print("STDERR:")
            print(cmd_result.stderr)
            results.append(cmd_result.dict())

        # Build Response object
        response_obj = Response(
            timestamp=datetime.datetime.now().isoformat(),
            results=results
        )

        # Append the formatted response to the conversation
        response_json = json.dumps(response_obj.dict(), indent=2)
        conversation.append({"role": "user", "content": response_json})

        # Proceed to next iteration
        # Read user input:
        # - c: continue the conversation
        # - q: quit the conversation

        user_input = input("Press 'c' to continue or 'q' to quit: ")
        if user_input == "q":
            break

