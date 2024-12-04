#!/usr/bin/env python3
import logging
from ami.os import OS

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create and initialize the OS
    os = OS()
    
    # TODO: Register apps here
    # Example:
    # from apps.browser import BrowserApp
    # os.register_app(BrowserApp("browser"))
    
    try:
        # Start the main event loop
        os.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()