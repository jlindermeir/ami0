import datetime
import json
import logging
import os
import pathlib
import base64

import openai
import paramiko
from openai import OpenAI
import tiktoken

from runtime.models import (
    CommandResponse,
    BrowserResponse,
    Request,
    Response
)
from runtime.browser import TextBasedBrowser

# Read the system prompt
system_prompt_file_path = pathlib.Path(__file__).parent / "prompts" / "system.md"
with open(system_prompt_file_path, "r") as f:
    system_prompt = f.read()

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("paramiko").setLevel(logging.WARNING)

OPENAI_MODEL = "gpt-4o"
ENCODING = tiktoken.encoding_for_model(OPENAI_MODEL)


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


def execute_commands(commands, ssh_config):
    """Execute a list of commands via SSH after user confirmation."""
    command_results = []
    for command in commands:
        execute_command = get_user_confirmation(f"Execute command '{command}'?", default='y')
        if not execute_command:
            logging.info(f"Skipping command '{command}'")
            command_results.append(CommandResponse(exit_code=-1, stdout="", stderr="Command skipped by user"))
            continue

        logging.info(f"Executing command '{command}' via SSH...")
        cmd_result = execute_ssh_command(
            ssh_config['host'], 
            ssh_config['port'], 
            ssh_config['username'], 
            ssh_config['password'], 
            command
        )
        logging.info(f"Exit code: {cmd_result.exit_code}")
        command_results.append(cmd_result)
    
    return command_results

def handle_browser_action(browser_action, browser):
    """Handle browser actions (navigation, clicks, and screenshots)."""
    if not browser_action:
        return None

    action = browser_action
    if action.action == "navigate":
        execute_action = get_user_confirmation(f"Navigate to URL '{action.target}'?", default='y')
        if not execute_action:
            logging.info(f"Skipping navigation to '{action.target}'")
            return BrowserResponse(url=action.target, content='Navigation skipped by user')
        
        logging.info(f"Navigating to URL '{action.target}'...")
        try:
            browser.navigate_to_url(action.target)
            return BrowserResponse(url=browser.page.url, content=browser.get_annotated_page_content())
        except Exception as e:
            logging.error(f"Error navigating to URL '{action.target}': {e}")
            return BrowserResponse(url=action.target, content=f"Error loading website: {e}")
            
    elif action.action == "click":
        execute_action = get_user_confirmation(f"Click element '{action.target}'?", default='y')
        if not execute_action:
            logging.info(f"Skipping click on element '{action.target}'")
            return BrowserResponse(url=browser.page.url, content='Click action skipped by user')
        
        logging.info(f"Clicking element '{action.target}'...")
        try:
            browser.click_element(int(action.target))
            return BrowserResponse(url=browser.page.url, content=browser.get_annotated_page_content())
        except Exception as e:
            logging.error(f"Error clicking element '{action.target}': {e}")
            return BrowserResponse(url=browser.page.url, content=f"Error clicking element: {e}")
    elif action.action == "screenshot":
        logging.info("Taking screenshot of current page...")
        success = browser.take_screenshot()
        return BrowserResponse(
            url=browser.page.url,
            content=browser.get_annotated_page_content(),
            has_screenshot=success
        )

def encode_image(image_path):
    """Encode image as base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def main():
    # SSH configuration
    ssh_config = {
        'host': os.getenv("SSH_HOST", "localhost"),
        'port': int(os.getenv("SSH_PORT", 2222)),
        'username': os.getenv("SSH_USERNAME", "root"),
        'password': os.getenv("SSH_PASSWORD", "DockerPass")
    }

    # Log initial configuration
    logging.info(f"SSH configuration: host={ssh_config['host']}, port={ssh_config['port']}, username={ssh_config['username']}")

    # Initialize the text-based browser
    browser = TextBasedBrowser()
    browser.setup_browser()

    # Conversation history
    conversation = []
    conversation.append({"role": "system", "content": system_prompt})
    conversation.append({"role": "user", "content": "Please provide the next set of commands."})

    # Initialize OpenAI client
    oai_client = OpenAI()

    while True:
        # Count tokens for the entire conversation as JSON
        conversation_json = json.dumps(conversation)
        num_tokens = len(ENCODING.encode(conversation_json))
        logging.info(f"Current conversation uses {num_tokens} tokens")

        # Send the conversation to the model and get parsed response
        try:
            completion = oai_client.beta.chat.completions.parse(
                model=OPENAI_MODEL,
                messages=conversation,
                temperature=1,
                max_tokens=2048,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                response_format=Request
            )
            request = completion.choices[0].message.parsed
            conversation.append({"role": "assistant", "content": completion.choices[0].message.content})
            
        except openai.RateLimitError as e:
            logging.error(f"OpenAI API rate limit reached: {e}")
            conversation.pop()
            conversation.append({"role": "system", "content": "OpenAI API rate limit reached. Please try producing shorter output."})
            continue

        # Output the thoughts to logs
        logging.info("Assistant's thoughts:")
        for thought in request.thoughts:
            logging.info(f"- {thought}")

        # Check if we have a final recommendation
        if request.recommendation:
            logging.info("Final recommendation received:")
            logging.info(f"Position: {request.recommendation.position}")
            logging.info(f"Confidence: {request.recommendation.confidence}")
            logging.info("Justifications:")
            for j in request.recommendation.justifications:
                logging.info(f"- {j}")
            
            # Ask user if they want to continue anyway
            if get_user_confirmation("Recommendation received. Exit now?", default='y'):
                break

        # Process commands and browser actions
        command_results = execute_commands(request.commands, ssh_config)
        browser_result = handle_browser_action(request.browser_action, browser)

        # Build Response object
        response_obj = Response(
            timestamp=datetime.datetime.now().isoformat(),
            results=command_results,
            browser_result=browser_result
        )

        # Create the next message content
        if browser_result and browser_result.has_screenshot:
            # If we have a screenshot, create a multi-part message with base64 encoding
            try:
                base64_image = encode_image(browser.screenshot_path)
                next_message = {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(response_obj.model_dump(), indent=2)
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            except Exception as e:
                logging.error(f"Error encoding screenshot: {e}")
                next_message = {
                    "role": "user",
                    "content": json.dumps(response_obj.model_dump(), indent=2)
                }
        else:
            # Otherwise, just send the regular JSON response
            next_message = {
                "role": "user",
                "content": json.dumps(response_obj.model_dump(), indent=2)
            }

        conversation.append(next_message)

        # Handle user input
        user_input = input(
            "Enter a message to send to the assistant, or 'q' to quit. Press Enter to continue without message: ").strip()
        if user_input.lower() == 'q':
            break
        elif user_input:
            conversation.append({"role": "system", "content": user_input})

    # Close the browser at the end
    browser.close()


if __name__ == "__main__":
    main()
