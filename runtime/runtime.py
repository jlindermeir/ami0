import datetime
import json
import os
import pathlib
import logging

import paramiko
from openai import OpenAI

from runtime.models import CommandResponse, Request, Response, request_json_schema


# Read the system prompt
system_prompt_file_path = pathlib.Path(__file__).parent / "prompts" / "system.md"
with open(system_prompt_file_path, "r") as f:
    system_prompt = f.read()

# Configure logging
logging.basicConfig(level=logging.INFO)

def get_user_confirmation(prompt, default='y'):
    valid_yes = ['y', 'yes']
    valid_no = ['n', 'no']
    prompt = f"{prompt} [{'Y/n' if default.lower() == 'y' else 'y/N'}]: "
    while True:
        choice = input(prompt).strip().lower()
        if not choice:
            choice = default.lower()
        if choice in valid_yes:
            return True
        elif choice in valid_no:
            return False
        else:
            print("Please respond with 'y' or 'n'.")

def get_user_choice(prompt, choices, default):
    choices_str = '/'.join(choices)
    prompt = f"{prompt} ({choices_str}), default is '{default}': "
    while True:
        choice = input(prompt).strip().lower()
        if not choice:
            choice = default.lower()
        if choice in choices:
            return choice
        else:
            print(f"Please choose from {choices_str}.")

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

    # Log initial configuration
    logging.info(f"SSH configuration: host={ssh_host}, port={ssh_port}, username={ssh_username}")

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
            model="gpt-4o",
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

        # Log assistant's reply
        logging.debug("Assistant's reply:")
        logging.debug(assistant_reply)

        # Parse assistant_reply into Request object
        try:
            # Remove code blocks if any
            if assistant_reply.startswith("```"):
                assistant_reply = assistant_reply.strip("```")
            # Parse JSON
            assistant_reply_json = json.loads(assistant_reply)
            request = Request(**assistant_reply_json)
        except Exception as e:
            logging.error("Error parsing assistant's reply into Request object: %s", e)
            logging.error("Assistant's reply was: %s", assistant_reply)
            # Handle error, perhaps send an error message to assistant
            error_message = f"Error parsing your response: {e}. Please make sure to respond in the correct JSON format."
            conversation.append({"role": "user", "content": error_message})
            continue

        # Output the thoughts to logs
        logging.info("Assistant's thoughts:")
        for thought in request.thoughts:
            logging.info(f"- {thought}")

        # For each command in commands list, send via SSH
        results = []
        for command in request.commands:
            # Prompt the user for confirmation if the command should be executed.
            execute_command = get_user_confirmation(f"Execute command '{command}'?", default='y')
            if not execute_command:
                logging.info(f"Skipping command '{command}'")
                results.append(CommandResponse(exit_code=-1, stdout="", stderr="Command skipped by user"))
                continue

            # Execute the command via SSH
            logging.info(f"Executing command '{command}' via SSH...")
            cmd_result = execute_ssh_command(ssh_host, ssh_port, ssh_username, ssh_password, command)

            logging.info(f"Exit code: {cmd_result.exit_code}")
            results.append(cmd_result.dict())

        # Build Response object
        response_obj = Response(
            timestamp=datetime.datetime.now().isoformat(),
            results=results
        )

        # Append the formatted response to the conversation
        response_json = json.dumps(response_obj.dict(), indent=2)
        conversation.append({"role": "user", "content": response_json})

        # Log the response
        logging.debug("Response sent to assistant:")
        logging.debug(response_json)

        # Proceed to next iteration
        user_choice = get_user_choice("Press 'c' to continue or 'q' to quit", ['c', 'q'], default='c')
        if user_choice == 'q':
            break

if __name__ == "__main__":
    main()
