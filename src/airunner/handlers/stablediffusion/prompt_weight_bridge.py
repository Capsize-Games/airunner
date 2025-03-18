import re


class PromptWeightBridge:
    """
    A bridge for converting prompt weights from A1111 syntax to compel syntax.
    """
    @classmethod
    def get_weight(cls, total, subtract=False):
        """
        Get the weight of the prompt.
        :param subtract:
        :param total: int
        :return: float
        """
        if not subtract:
            weight = pow(1.1, total)
            weight = round(weight, 2)
        else:
            weight = pow(1.1, total)
            weight = 2.0 - weight
            weight = round(weight, 2)
        if weight > 2.0:
            weight = 2.0
        elif weight < 0.0:
            weight = 0.0
        return weight

    @classmethod
    def convert_blend(cls, prompt):
        # find the pattern: ["word:word:0.1"]
        pattern = r"\[[^:\[0-9\]]+:[^:\[0-9\]]+:\d+\.\d+\]"
        compiled = re.compile(pattern)
        matches = compiled.findall(prompt)

        # replace with
        # ("word", "word").blend(0.1, 0.9)
        for match in matches:
            words = match[1:-1].split(":")
            weight = words.pop()
            words = tuple(words)
            weight_b = 1.0 - float(weight)
            replacement = f'("{words[0]}", "{words[1]}").blend({weight}, {weight_b})'
            prompt = prompt.replace(match, replacement)

        # find the pattern: ["word:word:0.1"]
        pattern = r"\([^:\(0-9\)]+:[^:\(0-9\)]+:\d+\.\d+\)"
        compiled = re.compile(pattern)
        matches = compiled.findall(prompt)

        # replace with
        # ("word", "word").blend(0.1, 0.9)
        for match in matches:
            words = match[1:-1].split(":")
            weight_b = words.pop()
            words = tuple(words)
            weight = 1.0 - float(weight_b)
            replacement = f'("{words[0]}", "{words[1]}").blend({weight}, {weight_b})'
            prompt = prompt.replace(match, replacement)
        return prompt

    @classmethod
    def convert_basic_brackets(cls, prompt):
        """
        Basic conversion of prompt syntax.
        Text surrounded with brackets decreases the weight of the prompt by 0.1

        Examples:
        [ABC] -> (ABC)0.9
        [[ABC]] -> (ABC)0.8

        :param prompt:str
        :return: prompt:str
        """
        pattern = r"(\[+[^:\[0-9\]]+\]+(?!\d)(?!\+)(?!\-))(?![^()]*\.blend\(\d+\.\d+,\s*\d+\.\d+\))"

        compiled = re.compile(pattern)
        matches = compiled.findall(prompt)

        for match in matches:
            # total_opening_parentheses = match.count("(")
            # weight = cls.get_weight(total_opening_parentheses)
            pattern = r"\](?!\d)"
            total_opening_parentheses = len(re.findall(pattern, match))
            weight = cls.get_weight(total_opening_parentheses, subtract=True)
            replacement = match.replace("[", "").replace("]", "")
            prompt = prompt.replace(match, f"({replacement}){weight}")
        return prompt

    @classmethod
    def convert_basic_parentheses(cls, prompt):
        """
        Basic conversion of prompt syntax.
        Text surrounded with parentheses increases the weight of the prompt by 0.1

        Examples:
        (ABC) -> (ABC)1.1
        ((ABC)) -> (ABC)1.2

        :param prompt:str
        :return: prompt:str
        """
        pattern = r"(\(+[^:(0-9)]+\)+(?!\d)(?!\+)(?!\-))(?![^()]*\.blend\(\d+\.\d+,\s*\d+\.\d+\))"

        compiled = re.compile(pattern)
        matches = compiled.findall(prompt)

        for match in matches:
            # total_opening_parentheses = match.count("(")
            # weight = cls.get_weight(total_opening_parentheses)
            pattern = r"\)(?!\d)"
            total_opening_parentheses = len(re.findall(pattern, match))
            weight = cls.get_weight(total_opening_parentheses)
            replacement = match.replace("(", "").replace(")", "")
            prompt = prompt.replace(match, f"({replacement}){weight}")
        return prompt

    @classmethod
    def convert_prompt_with_weight_value(cls, prompt):
        """
        Similar to convert_basic_parentheses but this time we are looking for
        values surrounded by parentheses followed by :<float>
        :param prompt:
        :return:
        """
        # find all values surrounded by parentheses followed by :<float>
        pattern = r"(\(([^:()]+):([0-9.]+)\))"
        matches = re.findall(pattern, prompt)

        # replace all matches with (match[0])<float>
        for match in matches:
            prompt = prompt.replace(match[0], f"({match[1]}){match[2]}")

        # find all values surrounded by parentheses followed by :<float>
        pattern = r"([^:() ]+):([0-9.]+)"
        matches = re.findall(pattern, prompt)

        # replace all matches with (match[0])<float>
        for match in matches:
            prompt = prompt.replace(f"{match[0]}:{match[1]}", f"({match[0]}){match[1]}")

        # find all opening parentheses that are not followed by a digit
        pattern = r"\(.*?\d\)(?!\d)"
        matches = re.findall(pattern, prompt)

        # find all closing parentheses that are not followed by a digit
        for match in matches:
            # do not replace blend patterns
            pattern = r'\(".*?", ".*?"\)\.blend\(\d+\.\d+,\s*\d+\.\d+\)'
            matches = re.findall(pattern, match)
            if matches:
                continue

            pattern = r"\)(?!\d)"
            total_opening_parentheses = len(re.findall(pattern, match))
            weight = cls.get_weight(total_opening_parentheses)

            # replace all matches with (match)<float>
            prompt = prompt.replace(match, f"{match}{weight}")
        return prompt

    @classmethod
    def reduce_weights(cls, prompt):
        """
        Reduce all weights over 1.4 to 1.4
        :param prompt:
        :return:
        """
        pattern = r"\d\.\d{2,}"
        matches = re.findall(pattern, prompt)

        for match in matches:
            if float(match) > 1.4:
                prompt = prompt.replace(match, "1.4")

        # also for single decimal weights
        pattern = r"\d\.\d"
        matches = re.findall(pattern, prompt)
        for match in matches:
            if float(match) > 1.4:
                prompt = prompt.replace(match, "1.4")
        return prompt

    @classmethod
    def convert_prompt_weights(cls, prompt):
        """
        Basic conversion of prompt syntax.
        Text surrounded with parentheses increases the weight of the prompt by 0.1

        Examples:
        (ABC) -> (ABC):1.1
        ((ABC)) -> ((ABC)):1.2

        :param prompt:str
        :return: prompt:str
        """
        prompt = cls.convert_blend(prompt)
        prompt = cls.convert_basic_parentheses(prompt)
        prompt = cls.convert_basic_brackets(prompt)
        prompt = cls.convert_prompt_with_weight_value(prompt)
        prompt = cls.reduce_weights(prompt)
        return prompt

    @classmethod
    def convert(cls, prompt):
        """
        Run all syntax conversions on a given prompt.
        :param prompt:str
        :return: prompt:str
        """
        if not prompt:
            return prompt
        prompt = cls.convert_prompt_weights(prompt)
        return prompt
