import re

class PromptWeightBridge:
    """
    A utility class for converting prompt weights between different syntaxes.
    """
    @classmethod
    def get_weight(cls, total: int, subtract: bool = False) -> float:
        """
        Calculate the weight of a prompt based on the total number of parentheses.

        :param total: The total number of parentheses.
        :param subtract: Whether to subtract the weight from 2.0.
        :return: The calculated weight.
        """
        weight = pow(1.1, total)
        if subtract:
            weight = 2.0 - weight
        return max(0.0, min(round(weight, 2), 2.0))

    @classmethod
    def convert_blend(cls, prompt: str) -> str:
        """
        Convert blend patterns in the prompt to a specific syntax.

        :param prompt: The input prompt string.
        :return: The converted prompt string.
        """
        pattern = r"\[[^:\[0-9\]]+:[^:\[0-9\]]+:\d+\.\d+\]"
        compiled = re.compile(pattern)
        matches = compiled.findall(prompt)
        for match in matches:
            words = match[1:-1].split(":")
            weight = words.pop()
            words = tuple(words)
            weight_b = 1.0 - float(weight)
            replacement = f'("{words[0]}", "{words[1]}").blend({weight}, {weight_b})'
            prompt = prompt.replace(match, replacement)
        return prompt

    @classmethod
    def convert_basic_brackets(cls, prompt: str) -> str:
        """
        Convert text surrounded by brackets to a weighted syntax.

        :param prompt: The input prompt string.
        :return: The converted prompt string.
        """
        pattern = r"(\[+[^:\[0-9\]]+\]+(?!\d)(?!\+)(?!\-))(?![^()]*\.blend\(\d+\.\d+,\s*\d+\.\d+\))"
        compiled = re.compile(pattern)
        matches = compiled.findall(prompt)
        for match in matches:
            total_opening_parentheses = len(re.findall(r"\](?!\d)", match))
            weight = cls.get_weight(total_opening_parentheses, subtract=True)
            replacement = match.replace("[", "").replace("]", "")
            prompt = prompt.replace(match, f"({replacement}){weight}")
        return prompt

    @classmethod
    def convert_basic_parentheses(cls, prompt: str) -> str:
        """
        Convert text surrounded by parentheses to a weighted syntax.

        :param prompt: The input prompt string.
        :return: The converted prompt string.
        """
        pattern = r"(\(+[^:(0-9)]+\)+(?!\d)(?!\+)(?!\-))(?![^()]*\.blend\(\d+\.\d+,\s*\d+\.\d+\))"
        compiled = re.compile(pattern)
        matches = compiled.findall(prompt)
        for match in matches:
            total_opening_parentheses = len(re.findall(r"\)(?!\d)", match))
            weight = cls.get_weight(total_opening_parentheses)
            replacement = match.replace("(", "").replace(")", "")
            prompt = prompt.replace(match, f"({replacement}){weight}")
        return prompt

    @classmethod
    def convert_prompt_weights(cls, prompt: str) -> str:
        """
        Apply all weight conversion methods to the prompt.

        :param prompt: The input prompt string.
        :return: The fully converted prompt string.
        """
        prompt = cls.convert_blend(prompt)
        prompt = cls.convert_basic_parentheses(prompt)
        prompt = cls.convert_basic_brackets(prompt)
        return prompt

    @classmethod
    def convert(cls, prompt: str) -> str:
        """
        Run all syntax conversions on a given prompt.

        :param prompt: The input prompt string.
        :return: The converted prompt string.
        """
        if not prompt:
            return prompt
        return cls.convert_prompt_weights(prompt)
