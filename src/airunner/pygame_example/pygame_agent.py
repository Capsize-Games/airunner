from airunner.handlers.llm.agent.agents import LocalAgent


class PygameAgent(LocalAgent):
    """
    This is an example of a Pygame agent that can be used with the Pygame window.
    It inherits from the LocalAgent class and implements the system_prompt property.
    The system_prompt is used to provide the agent with a specific instruction set
    for interacting with the Pygame window.
    """
    @property
    def system_prompt(self) -> str:
        return """You are a game AI that can interact with the Pygame window."""