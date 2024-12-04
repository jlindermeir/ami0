from typing import Optional, Type, Union, List, Dict, Any
from openai import OpenAI
from pydantic import BaseModel, Field, create_model
import logging

from .app import App
from .models import LaunchAppResponse, ExitAppResponse

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
    
    def __init__(self):
        self.client = OpenAI()
        self.apps: dict[str, App] = {}
        self.current_app: Optional[App] = None
        self.conversation: List[Dict[str, str]] = []
        
    def register_app(self, app: App) -> None:
        """Register a new app with the system."""
        self.apps[app.name] = app
    
    @property
    def system_prompt(self) -> str:
        """Generate the system prompt based on current state."""
        base_prompt = (
            "You are an autonomous AI agent operating in a structured environment. "
            "Your task is to interact with the available apps to achieve your goals. "
            "Your responses must follow the specified format exactly. "
            "You should explain your reasoning in the thought field before taking any action."
        )
        
        if self.current_app is None:
            # Home screen prompt
            app_list = "\n".join(f"- {name}: {app.description}" 
                               for name, app in self.apps.items())
            return f"{base_prompt}\n\nAvailable apps:\n{app_list}"
        else:
            # App-specific prompt
            return f"{base_prompt}\n\n{self.current_app.description}\n\nYou can return to the home screen by choosing to exit the app."
    
    @property
    def current_response_format(self) -> Type[BaseModel]:
        """Get the current expected response format."""
        if self.current_app is None:
            # In home screen, only allow launching apps
            return create_model(
                "HomeResponse",
                thought=(str, Field(description="Your reasoning for this action")),
                __base__=LaunchAppResponse
            )
        else:
            # In app, allow either app-specific actions or exiting
            app_format = self.current_app.current_response_format
            exit_format = create_model(
                "ExitWithThought",
                thought=(str, Field(description="Your reasoning for this action")),
                __base__=ExitAppResponse
            )
            
            # Create a union of the app response and exit response
            return create_model(
                f"AppResponse",
                thought=(str, Field(description="Your reasoning for this action")),
                action=(Union[app_format, exit_format], Field(...)),
            )
    
    def handle_agent_action(self, response: Any) -> Optional[str]:
        """Handle an agent's action, returning any result from the app."""
        # First, log the agent's thought process
        logging.info(f"Agent's thought: {response.thought}")
        
        # Handle the response based on current state
        if isinstance(response, LaunchAppResponse):
            # Ask for confirmation before launching app
            if not get_user_confirmation(f"Allow agent to launch app '{response.app_name}'?"):
                return "Action denied by user"
                
            if response.app_name in self.apps:
                self.current_app = self.apps[response.app_name]
                return f"Launched app: {response.app_name}"
            else:
                raise ValueError(f"Unknown app: {response.app_name}")
                
        elif isinstance(response.action, ExitAppResponse):
            # Ask for confirmation before exiting app
            if not get_user_confirmation(f"Allow agent to exit app '{self.current_app.name}'?"):
                return "Action denied by user"
                
            self.current_app = None
            return "Returned to home screen"
            
        else:
            if self.current_app is None:
                raise ValueError("No app is currently active")
                
            # Ask for confirmation before executing app action
            action_desc = str(response.action)  # Get string representation of the action
            if not get_user_confirmation(f"Allow agent to perform action in {self.current_app.name}?\nAction: {action_desc}"):
                return "Action denied by user"
                
            return self.current_app.handle_response(response.action)
    
    def run(self):
        """Main event loop."""
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
                # Get next action from model
                completion = self.client.beta.chat.completions.parse(
                    model="gpt-4o-2024-08-06",
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        *self.conversation[-10:]  # Keep last 10 messages for context
                    ],
                    response_format=self.current_response_format,
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
                print(f"Current state: {state}")
                
                # Add prompt for next action
                self.conversation.append({
                    "role": "user",
                    "content": "What would you like to do next? Please explain your reasoning."
                })
                
            except KeyboardInterrupt:
                print("\nShutting down...")
                break
            except Exception as e:
                logging.error(f"Error: {str(e)}")
                self.conversation.append({
                    "role": "system",
                    "content": f"Error occurred: {str(e)}"
                })