import logging
from typing import Type, List, Literal
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright, TimeoutError
from pydantic import BaseModel, Field

from ami.app import App

class NavigateAction(BaseModel):
    """Action for navigating to a URL."""
    type: Literal["navigate"]
    url: str = Field(description="URL to navigate to")

class ClickAction(BaseModel):
    """Action for clicking an element."""
    type: Literal["click"]
    element: int = Field(description="Element number to click (as shown in <N>)")

class BrowserApp(App):
    """A text-based browser app using Playwright."""
    
    def __init__(self, name: str = "browser", headless: bool = True):
        super().__init__(name)
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/116.0.0.0 Safari/537.36"
        )
        
        # Initialize browser on startup
        self.setup_browser()
    
    def setup_browser(self):
        """Set up the Playwright browser and context."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(user_agent=self.user_agent)
        self.page = self.context.new_page()
        logging.info("Browser setup complete.")
    
    @property
    def description(self) -> str:
        return (
            "A text-based browser that allows you to navigate websites and click elements. "
            "Elements that can be clicked are annotated with numbers in <N> format."
        )
    
    @property
    def usage_prompt(self) -> str:
        current_url = self.page.url if self.page else "No page loaded"
        return f"""
This is the Browser app. You can navigate to URLs and click on elements.

Current URL: {current_url}

Available actions:
1. Navigate to a URL:
{{
    "type": "navigate",
    "url": "https://example.com"
}}

2. Click an element (using the number shown in <N>):
{{
    "type": "click",
    "element": 1
}}

The page content will show clickable elements marked with <N> where N is the element number.
For example, "Click here<1>" means you can click this element using element number 1.
""".strip()
    
    def get_action_models(self) -> List[Type[BaseModel]]:
        """Return the action models supported by this app."""
        return [NavigateAction, ClickAction]
    
    def annotate_clickable_elements(self):
        """Annotate clickable elements with option numbers."""
        selector = "a[href], button, input[type=button], input[type=submit], input[type=reset]"
        elements = self.page.query_selector_all(selector)

        if not elements:
            logging.warning("No clickable links or buttons found.")
            return []

        for i, element in enumerate(elements):
            option_number = i + 1
            text = element.inner_text().strip()
            if not text:
                text = element.get_attribute('value') or '[No text]'
            
            # Annotate the element's text content with the option number
            element.evaluate(
                "(el, num) => { el.textContent = el.textContent.trim() + ' <' + num + '>'; }", 
                option_number
            )
    
    def get_annotated_page_content(self) -> str:
        """Get the text content of the page with annotated elements."""
        self.annotate_clickable_elements()
        body_text = self.page.evaluate("document.body.innerText")
        logging.debug("Page text retrieved.")
        return body_text
    
    def navigate_to_url(self, url: str) -> str:
        """Navigate to the specified URL and return the page content."""
        try:
            self.page.goto(url, wait_until='networkidle')
            logging.info(f"Navigated to URL: {url}")
            return self.get_annotated_page_content()
        except Exception as e:
            logging.error(f"Failed to load URL {url}: {e}")
            raise
    
    def click_element(self, element_number: int) -> str:
        """Click the element with the specified number and return the new page content."""
        elements = self.page.query_selector_all(
            "a[href], button, input[type=button], input[type=submit], input[type=reset]"
        )
        if element_number < 1 or element_number > len(elements):
            raise ValueError(f"Invalid element number {element_number}. Valid range: 1-{len(elements)}")
        
        element = elements[element_number - 1]
        href = element.get_attribute('href')

        if href:
            url = urljoin(self.page.url, href)
            return self.navigate_to_url(url)
        else:
            try:
                element.click()
                self.page.wait_for_load_state('networkidle')
                logging.info(f"Clicked element and navigated to: {self.page.url}")
                return self.get_annotated_page_content()
            except TimeoutError:
                logging.error("Timed out waiting for page to load after click.")
                raise
            except Exception as e:
                logging.error(f"Error clicking the element: {e}")
                raise
    
    def handle_response(self, response: BaseModel) -> str:
        """Handle browser actions and return the page content."""
        if isinstance(response, NavigateAction):
            return self.navigate_to_url(response.url)
        elif isinstance(response, ClickAction):
            return self.click_element(response.element)
        else:
            raise ValueError(f"Unknown action type: {type(response)}")
    
    def __del__(self):
        """Cleanup browser resources."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logging.info("Browser closed.") 