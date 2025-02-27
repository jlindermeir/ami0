#!/usr/bin/env python3
import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from ami.os import OS
from ami.apps import SSHApp, BrowserApp

### Configuration:
# Run the Playwright browser in headless mode
BROWSER_HEADLESS = False

def setup_logging():
    """Configure detailed logging with both file and console output."""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Create a unique log file for this session
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f'logs/ami_{timestamp}.log'
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            # File handler with debug level
            logging.FileHandler(log_file),
            # Console handler with info level
            logging.StreamHandler()
        ]
    )
    
    # Set debug level for our module
    logging.getLogger('ami').setLevel(logging.INFO)
    
    # Reduce noise from other libraries
    logging.getLogger('openai').setLevel(logging.INFO)
    logging.getLogger('paramiko').setLevel(logging.WARNING)
    
    logging.info(f"Logging initialized. Log file: {log_file}")

def main():
    # Read environment variables from .env file
    load_dotenv()
    
    # Set up logging first
    setup_logging()
    
    # Set the model
    model = "gpt-4o"
    
    # Read the user prompt
    prompt_path = Path(__file__).parent / "prompts" / "system.md"
    with open(prompt_path, 'r') as f:
        user_prompt = f.read().strip()
    
    # Create and initialize the OS
    os = OS(model=model, user_prompt=user_prompt)
    
    # Register our apps
    os.register_app(BrowserApp(headless=BROWSER_HEADLESS))
    os.register_app(SSHApp())
    
    try:
        # Start the main event loop
        os.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()