from typing import Optional, Type, Union, List, Dict, Any
import json
import logging
from enum import Enum
from openai import OpenAI
from pydantic import BaseModel, Field, create_model

from .app import App
from .models import BaseResponse, LaunchAppAction, ExitAppAction

# Create module-level logger
logger = logging.getLogger(__name__)

def get_user_confirmation(prompt: str, default: str = 'y') -> bool:
    """Get user confirmation for an action."""
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

class OS:
    """Main operating system class that manages apps and handles the event loop."""
    
    def __init__(self, model: str = "gpt-4o-2024-08-06"):
        self.client = OpenAI()
        self.model = model
        self.apps: dict[str, App] = {}
        self.current_app: Optional[App] = None
        self.conversation: List[Dict[str, str]] = []
        self._app_enum: Optional[Type[Enum]] = None
        logger.info(f"Initialized OS with model: {model}")
    
    def _create_app_enum(self) -> Type[Enum]:
        """Create an enum of available apps."""
        if not self.apps:
            raise ValueError("No apps registered")
        
        # Create enum dynamically
        return Enum('AvailableApps', {
            app_name: app_name for app_name in self.apps.keys()
        })
    
    def register_app(self, app: App) -> None:
        """Register a new app with the system."""
        logger.info(f"Registering app: {app.name}")
        self.apps[app.name] = app
        # Recreate enum when apps change
        self._app_enum = self._create_app_enum()
    
    @property
    def system_prompt(self) -> str:
        """Generate the system prompt based on current state."""
        base_prompt = (
            "You are an autonomous AI agent operating in a structured environment. "
            "Your task is to interact with the available apps to achieve your goals. "
            "Your responses must follow the specified format exactly. "
            "You should explain your reasoning in the thoughts array, with each step as a separate thought."
        )
        
        if self.current_app is None:
            # Home screen prompt
            app_list = "\n".join(f"- {name}: {app.description}" 
                               for name, app in self.apps.items())
            prompt = f"{base_prompt}\n\nAvailable apps:\n{app_list}"
        else:
            # App-specific prompt
            prompt = f"{base_prompt}\n\n{self.current_app.description}\n\nYou can return to the home screen by choosing to exit the app."
        
        logger.debug(f"Generated system prompt:\n{prompt}")
        return prompt
    
    @property
    def current_response_format(self) -> Type[BaseModel]:
        """Get the current expected response format."""
        if self.current_app is None:
            # In home screen, only allow launching apps with enum values
            launch_action = create_model(
                "LaunchAppAction",
                app_name=(self._app_enum, Field(description="The app to launch")),
                __base__=LaunchAppAction
            )
            
            format = create_model(
                "HomeResponse",
                action=(launch_action, Field(description="The action to take")),
                __base__=BaseResponse
            )
            logger.debug("Using home screen response format")
        else:
            # In app, allow app-specific actions or exiting
            possible_actions = [*self.current_app.get_action_models(), ExitAppAction]
            
            format = create_model(
                f"AppResponse",
                action=(Union[tuple(possible_actions)], Field(description="The action to take")),
                __base__=BaseResponse
            )
            logger.debug(f"Using app response format for {self.current_app.name}")
        
        # Log the complete schema
        schema = format.model_json_schema()
        logger.debug(f"Response format schema:\n{json.dumps(schema, indent=2)}")
        
        return format
    
    def handle_agent_action(self, response: Any) -> Optional[str]:
        """Handle an agent's action, returning any result from the app."""
        # Log the complete response for debugging
        logger.debug(f"Agent response:\n{response.model_dump_json(indent=2)}")
        logger.info("Agent's thoughts:")
        for i, thought in enumerate(response.thoughts, 1):
            logger.info(f"  {i}. {thought}")
        
        action = response.action
        
        # Handle the response based on action type
        if action.type == "launch_app":
            app_name = action.app_name.value  # Get string value from enum
            logger.info(f"Agent wants to launch app: {app_name}")
            # Ask for confirmation before launching app
            if not get_user_confirmation(f"Allow agent to launch app '{app_name}'?"):
                logger.info("User denied app launch")
                return "Action denied by user"
                
            self.current_app = self.apps[app_name]  # Will always exist due to enum
            logger.info(f"Launched app: {app_name}")
            return f"Launched app: {app_name}"
                
        elif action.type == "exit_app":
            logger.info(f"Agent wants to exit app: {self.current_app.name}")
            # Ask for confirmation before exiting app
            if not get_user_confirmation(f"Allow agent to exit app '{self.current_app.name}'?"):
                logger.info("User denied app exit")
                return "Action denied by user"
                
            app_name = self.current_app.name
            self.current_app = None
            logger.info(f"Exited app: {app_name}")
            return "Returned to home screen"
            
        else:
            if self.current_app is None:
                logger.error("Attempted app action without active app")
                raise ValueError("No app is currently active")
                
            # Ask for confirmation before executing app action
            action_desc = str(action)  # Get string representation of the action
            logger.info(f"Agent wants to perform action in {self.current_app.name}: {action_desc}")
            
            if not get_user_confirmation(f"Allow agent to perform action in {self.current_app.name}?\nAction: {action_desc}"):
                logger.info("User denied app action")
                return "Action denied by user"
            
            try:
                result = self.current_app.handle_response(action)
                logger.info(f"App action result: {result}")
                return result
            except Exception as e:
                logger.error(f"Error executing app action: {str(e)}", exc_info=True)
                raise
    
    def run(self):
        """Main event loop."""
        if not self._app_enum:
            raise ValueError("No apps registered. Please register at least one app before running.")
            
        logger.info("Starting autonomous agent system")
        print("Starting autonomous agent system")
        print("The agent will request permission before taking any actions.")
        print("Initial state: Home Screen")
        
        # Initial prompt to start the agent
        self.conversation.append({
            "role": "user",
            "content": "What would you like to do? Please explain your reasoning."
        })
        
        while True:
            try:
                # Log conversation state
                logger.debug(f"Current conversation state:\n{json.dumps(self.conversation[-10:], indent=2)}")
                
                # Get next action from model
                logger.info("Requesting next action from agent")
                
                # Get and log the current response format
                response_format = self.current_response_format
                
                completion = self.client.beta.chat.completions.parse(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        *self.conversation[-10:]  # Keep last 10 messages for context
                    ],
                    response_format=response_format,
                )
                
                response = completion.choices[0].message.parsed
                
                # Handle the action and get any results
                result = self.handle_agent_action(response)
                
                # Add the result to the conversation if there was one
                if result:
                    self.conversation.append({
                        "role": "system",
                        "content": result
                    })
                    print(f"\nResult: {result}")
                
                # Print current state
                state = "Home Screen" if self.current_app is None else f"In {self.current_app.name}"
                logger.info(f"Current state: {state}")
                print(f"Current state: {state}")
                
                # Add prompt for next action
                self.conversation.append({
                    "role": "user",
                    "content": "What would you like to do next? Please explain your reasoning."
                })
                
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                print("\nShutting down...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}", exc_info=True)
                self.conversation.append({
                    "role": "system",
                    "content": f"Error occurred: {str(e)}"
                })