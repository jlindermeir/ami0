from typing import Optional, Type, Union, List, Dict, Any, Tuple, Literal
import json
import logging
from openai import OpenAI
from pydantic import BaseModel, Field, create_model

from .app import App
from .models import BaseResponse, LaunchAppAction, ExitAppAction

# Create module-level logger
logger = logging.getLogger(__name__)

# OS system prompt that explains the app system
OS_SYSTEM_PROMPT = """
You are an autonomous AI agent operating in a structured environment with multiple apps.
Each app provides specific functionality that you can use to achieve your goals.

You can:
- Launch apps from the home screen
- Use app-specific actions when inside an app
- Return to the home screen at any time

Your responses must follow this format:
{
    "thoughts": ["thought1", "thought2", ...],  # Explain your reasoning
    "action": {
        "type": "action_type",
        ...action specific fields...
    }
}

The available actions depend on your current state (home screen or inside an app).
""".strip()

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
    
    def __init__(self, model: str = "gpt-4o-2024-08-06", user_prompt: Optional[str] = None):
        self.client = OpenAI()
        self.model = model
        self.apps: dict[str, App] = {}
        self.current_app: Optional[App] = None
        self.conversation: List[Dict[str, Any]] = []
        
        # Initialize conversation with prompts
        if user_prompt:
            self.conversation.append({
                "role": "system",
                "content": user_prompt
            })
        
        self.conversation.append({
            "role": "system",
            "content": OS_SYSTEM_PROMPT
        })
        
        logger.info(f"Initialized OS with model: {model}")
    
    def register_app(self, app: App) -> None:
        """Register a new app with the system."""
        logger.info(f"Registering app: {app.name}")
        self.apps[app.name] = app
    
    @property
    def system_prompt(self) -> str:
        """Generate the system prompt based on current state."""
        if self.current_app is None:
            # Home screen prompt
            app_list = "\n".join(f"- {name}: {app.description}" 
                               for name, app in self.apps.items())
            prompt = f"Available apps:\n{app_list}"
        else:
            # App-specific prompt
            prompt = "You can return to the home screen by choosing to exit the app."
        
        logger.debug(f"Generated system prompt:\n{prompt}")
        return prompt
    
    @property
    def current_response_format(self) -> Type[BaseModel]:
        """Get the current expected response format."""
        if self.current_app is None:
            # In home screen, only allow launching apps with literal union
            app_names = list(self.apps.keys())
            if not app_names:
                raise ValueError("No apps registered")
            
            # Create a union of literals for app names
            AppNameType = Literal[tuple(app_names)]  # type: ignore
            
            launch_action = create_model(
                "LaunchAppAction",
                app_name=(AppNameType, Field(description="The app to launch")),
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
    
    def _format_conversation_message(self, text: str, image: Optional[str] = None) -> Dict[str, Any]:
        """Format a message for the conversation, optionally including an image."""
        if not image:
            content = text
        else:
            content = [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}}
            ]
        
        return {"role": "user", "content": content}
    
    def handle_agent_action(self, response: Any) -> Tuple[str, Optional[str]]:
        """Handle an agent's action, returning (text_response, optional_base64_image)."""
        # Log the complete response for debugging
        logger.debug(f"Agent response:\n{response.model_dump_json(indent=2)}")
        logger.info("Agent's thoughts:")
        for i, thought in enumerate(response.thoughts, 1):
            logger.info(f"  {i}. {thought}")
        
        action = response.action
        
        # Handle the response based on action type
        if action.type == "launch_app":
            app_name = action.app_name  # Now a string literal
            logger.info(f"Agent wants to launch app: {app_name}")
            # Ask for confirmation before launching app
            if not get_user_confirmation(f"Allow agent to launch app '{app_name}'?"):
                logger.info("User denied app launch")
                return ("Action denied by user", None)
                
            self.current_app = self.apps[app_name]  # Will always exist due to literal union
            
            # Add app usage prompt to conversation
            self.conversation.append({
                "role": "system",
                "content": self.current_app.usage_prompt
            })
            
            logger.info(f"Launched app: {app_name}")
            return (f"Launched app: {app_name}", None)
                
        elif action.type == "exit_app":
            logger.info(f"Agent wants to exit app: {self.current_app.name}")
            # Ask for confirmation before exiting app
            if not get_user_confirmation(f"Allow agent to exit app '{self.current_app.name}'?"):
                logger.info("User denied app exit")
                return ("Action denied by user", None)
                
            app_name = self.current_app.name
            self.current_app = None
            logger.info(f"Exited app: {app_name}")
            return ("Returned to home screen", None)
            
        else:
            if self.current_app is None:
                logger.error("Attempted app action without active app")
                raise ValueError("No app is currently active")
                
            # Ask for confirmation before executing app action
            action_desc = str(action)  # Get string representation of the action
            logger.info(f"Agent wants to perform action in {self.current_app.name}: {action_desc}")
            
            if not get_user_confirmation(f"Allow agent to perform action in {self.current_app.name}?\nAction: {action_desc}"):
                logger.info("User denied app action")
                return ("Action denied by user", None)
            
            try:
                return self.current_app.handle_response(action)
            except Exception as e:
                logger.error(f"Error executing app action: {str(e)}", exc_info=True)
                raise
    
    def run(self):
        """Main event loop."""
        if not self.apps:
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
                        *self.conversation
                    ],
                    response_format=response_format,
                )
                
                response = completion.choices[0].message.parsed
                
                # Add agent's response to conversation
                self.conversation.append({
                    "role": "assistant",
                    "content": json.dumps({
                        "thoughts": response.thoughts,
                        "action": response.action.model_dump()
                    }, indent=2)
                })
                
                # Handle the action and get any results
                text, image = self.handle_agent_action(response)
                
                # Add the result to the conversation if there was one
                if text:
                    self.conversation.append(self._format_conversation_message(text, image))
                    print(f"\nResult: {text}")
                    
                if image:
                    print(f"[Image data: {len(image)} bytes]")
                
                # Print current state
                state = "Home Screen" if self.current_app is None else f"In {self.current_app.name}"
                logger.info(f"Current state: {state}")
                print(f"Current state: {state}")
                
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