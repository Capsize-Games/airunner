from airunner.app import App


class API(App):    
    def send_llm_request(self, prompt: str):
        self.app.main_window.send_llm_request(prompt)
    
    def quit(self):
        self.app.quit()
