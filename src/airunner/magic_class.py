import importlib
import enum

from airunner.aihandler.llm.agent.ai_runner_agent import AIRunnerAgent


class State(enum.Enum):
    IDLE = 1
    PROCESSING = 2
    TESTING = 3
    SUCCESS = 4
    FAIL = 5


class MagicClass:
    def __init__(self, agent: AIRunnerAgent):
        self.loaded_modules = {}
        self.function_cache = {}
        self.function_docs = {}
        self.dynamic_attributes = {}
        self.agent: AIRunnerAgent = agent

    def dynamic_import(self, module_name):
        """Dynamically imports a module if not already imported."""
        if module_name not in self.loaded_modules:
            self.loaded_modules[module_name] = importlib.import_module(module_name)
        return self.loaded_modules[module_name]

    def __getattr__(self, attribute):
        """Handle calls to non-existent methods or access to dynamic properties."""
        if attribute in self.dynamic_attributes:
            return self.dynamic_attributes[attribute]

        if attribute.startswith('create_'):
            return self.class_factory(attribute.split('create_')[1])

        def method(*args, **kwargs):
            prompt = f"{attribute} with arguments {args} and keyword arguments {kwargs}"
            prompt += f". Available methods: {self.generate_method_context()}"
            code, test_code, doc = self.query_llm_for_code_test_and_docs(prompt)
            exec(code)
            result = locals().get('result', None)
            if self.run_test(test_code):
                self.state = State.SUCCESS
            else:
                self.state = State.FAIL
            self.function_cache[attribute] = method
            self.function_docs[attribute] = doc
            return result
        return method

    def __setattr__(self, name, value):
        """Intercept attribute assignments and handle them dynamically."""
        if name in ['loaded_modules', 'function_cache', 'function_docs', 'dynamic_attributes', '__dict__']:
            super().__setattr__(name, value)
        else:
            self.dynamic_attributes[name] = value

    def class_factory(self, class_name):
        """Dynamically create and return an instance of MagicClass to simulate a new class."""
        print(f"Creating new dynamic class instance: {class_name}")
        return MagicClass()

    def generate_method_context(self):
        """Generate a context string that includes descriptions of all available methods."""
        descriptions = [f"{name}: {doc}" for name, doc in self.function_docs.items()]
        return " ".join(descriptions)

    def query_llm_for_code_test_and_docs(self, prompt):
        """Simulate querying an LLM which returns Python code, test code, and documentation."""
        print(f"Received prompt: {prompt}")
        code = 'result = "output from dynamic function"'
        test_code = '''
import unittest

class TestDynamicFunction(unittest.TestCase):
    def test_output(self):
        self.assertEqual(result, "output from dynamic function")

unittest.main(argv=[''], exit=False)
'''
        doc = "Calculates and returns a dynamic output based on inputs."
        return (code, test_code, doc)

    def run_test(self, test_code):
        """Run dynamically generated test code and return the outcome as True (pass) or False (fail)."""
        try:
            exec(test_code)
            return True
        except AssertionError:
            return False
