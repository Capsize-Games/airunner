import random


class BuildPrompt:
    @classmethod
    def process_variable(cls, var):
        if isinstance(var, dict):
            if "range" in var:
                if "type" in var and var["type"] == "range":
                    var = random.randint(var["min"], var["max"])
        return var

    @classmethod
    def has_variable(cls, variable, available_variables):
        return variable in available_variables and available_variables[variable] != [""]

    @classmethod
    def add_text_to_prompt(
        cls,
        prompt,
        text,
        cond,
        cond_val,
        not_cond,
        not_cond_val,
        or_cond,
        or_cond_val,
        else_cond,
        else_cond_val
    ):
        cond_true = (cond and cond_val) or (not cond)
        not_cond_true = (not_cond and not not_cond_val) or (not not_cond)
        or_cond_true = (or_cond and or_cond_val) or (not or_cond)

        if cond_true and not_cond_true and or_cond_true:
            if text:
                return prompt + text, True
            else:
                return prompt, True
        elif else_cond and else_cond_val:
            if text:
                return prompt + else_cond, True
            else:
                return prompt, True
        return prompt, False

    @classmethod
    def build_conditional_prompt(cls, conditionals, vars, category, prompt=""):
        for conditional in conditionals:
            text = None
            cond = None
            not_cond = None
            or_cond = None
            next = []
            else_cond = None
            if "text" in conditional:
                text = conditional["text"]
            if "cond" in conditional:
                cond = conditional["cond"]
            if "not_cond" in conditional:
                not_cond = conditional["not_cond"]
            if "next" in conditional:
                next = conditional["next"]
            if "else" in conditional:
                else_cond = conditional["else"]
            if "or_cond" in conditional:
                or_cond = conditional["or_cond"]

            if not text and len(next) == 0:
                continue

            if cond:
                has_cond = True
                if isinstance(cond, list):
                    for cond_var in cond:
                        if not cls.has_variable(cond_var, vars):
                            has_cond = False
                else:
                    if not cls.has_variable(cond, vars):
                        has_cond = False
            else:
                has_cond = False

            if not_cond:
                not_cond_val = False
                if isinstance(not_cond, list):
                    for not_cond_var in not_cond:
                        if cls.has_variable(not_cond_var, vars):
                            not_cond_val = True
                else:
                    if cls.has_variable(not_cond, vars):
                        not_cond_val = True
            else:
                not_cond_val = True

            else_cond_val = False
            if else_cond:
                if isinstance(else_cond, list):
                    for else_cond_var in else_cond:
                        if cls.has_variable(else_cond_var, vars):
                            else_cond_val = True
                            break
                else:
                    if cls.has_variable(else_cond, vars):
                        else_cond_val = True

            or_cond_val = False
            if or_cond:
                if isinstance(or_cond, list):
                    for or_cond_var in or_cond:
                        if cls.has_variable(or_cond_var, vars):
                            or_cond_val = True
                            break
                else:
                    if cls.has_variable(or_cond, vars):
                        or_cond_val = True

            prompt, success = cls.add_text_to_prompt(
                prompt,
                text,
                cond,
                has_cond,
                not_cond,
                not_cond_val,
                or_cond,
                or_cond_val,
                else_cond,
                else_cond_val
            )

            if success:
                for next_conditionals in next:
                    prompt = cls.build_conditional_prompt(
                        next_conditionals,
                        vars,
                        category,
                        prompt
                    )

        return prompt

    @classmethod
    def build_prompt(cls, conditionals, vars, category):
        prompt = cls.build_conditional_prompt(
            conditionals,
            vars,
            category)
        return prompt.strip()
