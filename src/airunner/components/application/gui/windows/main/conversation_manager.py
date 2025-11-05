

class ConversationManager:
    """
    Handles conversation and prompt management logic for MainWindow.
    """

    def __init__(self, api, logger=None):
        self.api = api
        self.logger = logger
        if self.logger:
            self.logger.debug("ConversationManager initialized.")

    def clear_all_prompts(self, main_window):
        if self.logger:
            self.logger.info("Clearing all prompts.")
        main_window.prompt = ""
        main_window.negative_prompt = ""
        self.api.clear_prompts()
        if self.logger:
            self.logger.debug("Prompts cleared and API notified.")

    def create_saved_prompt(self, main_window, data):
        if self.logger:
            self.logger.info(f"Saving prompt: {data}")
        # Implement actual save logic here
