import logging
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, TimeoutError


class TextBasedBrowser:
    """A text-based browser using Playwright."""

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/116.0.0.0 Safari/537.36"
        )

    def setup_browser(self):
        """Set up the Playwright browser and context with a custom user agent."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context(user_agent=self.user_agent)
        self.page = self.context.new_page()
        logging.info("Browser setup complete.")

    def navigate_to_url(self, url):
        """Navigate to the specified URL."""
        try:
            self.page.goto(url, wait_until='networkidle')
            logging.info(f"Navigated to URL: {url}")
        except Exception as e:
            logging.error(f"Failed to load URL {url}: {e}")
            raise

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

    def get_annotated_page_content(self):
        """Get the text content of the page after annotation."""
        self.annotate_clickable_elements()
        body_text = self.page.evaluate("document.body.innerText")
        logging.debug("Page text retrieved.")
        return body_text

    def click_element(self, element_number):
        """Click the element with the specified option number."""
        elements = self.page.query_selector_all(
            "a[href], button, input[type=button], input[type=submit], input[type=reset]"
        )
        if element_number < 1 or element_number > len(elements):
            raise ValueError("Invalid element number.")
        
        element = elements[element_number - 1]
        href = element.get_attribute('href')

        if href:
            url = urljoin(self.page.url, href)
            self.navigate_to_url(url)
        else:
            try:
                element.click()
                self.page.wait_for_load_state('networkidle')
                logging.info(f"Clicked element and navigated to: {self.page.url}")
            except TimeoutError:
                logging.error("Timed out waiting for page to load after click.")
                raise
            except Exception as e:
                logging.error(f"Error clicking the element: {e}")
                raise

    def close(self):
        """Close browser resources."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logging.info("Browser closed.")

    def run(self):
        """Run the text-based browser (not used in integration)."""
        pass  # Removed interactive loop for integration


if __name__ == '__main__':
    browser = TextBasedBrowser()
    browser.run()
