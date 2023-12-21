import json
import random

from airunner.prompt_builder.prompt_parser import PromptParser
from airunner.build_prompt import BuildPrompt
from airunner.utils import get_session
from airunner.data.models import PromptVariableCategory, PromptCategory, PromptVariableCategoryWeight, PromptVariable, PromptOption, PromptStyleCategory, PromptStyle


class PromptData:
    data = None
    prompt_variables = {}
    categories = []
    genres = []
    colors = []
    styles = []
    variables = None
    weighted_variables = {}
    current_prompt = ""
    current_negative_prompt = ""
    text_prompt_weight = 0.0
    auto_prompt_weight = 1.0
    negative_text_prompt_weight = 0.0
    negative_auto_prompt_weight = 1.0
    seed = 42
    category = "Random"
    image_genre = "Random"
    image_color = "Random"
    image_style = "Random"
    advanced = False
    prompt_prefix = ""
    prompt_suffix = ""
    negative_prompt_prefix = ""
    negative_prompt_suffix = ""
    current_prompt_category_id = None

    def __init__(self, prompt_id, use_prompt_builder=False):
        self.current_prompt_category_id = prompt_id
        self.refresh_data()
        self.use_prompt_builder = use_prompt_builder
    
    def change_prompt(self, prompt_id):
        if prompt_id != self.current_prompt_category_id:
            self.current_prompt_category_id = prompt_id
            self.refresh_data()
    
    def refresh_data(self):
        self.prepare_data(self.current_prompt_category_id)

    def build_prompts(self, **kwargs):
        self.current_prompt = kwargs.get("prompt", self.current_prompt)
        self.current_negative_prompt = kwargs.get("negative_prompt", self.current_negative_prompt)
        self.text_prompt_weight = kwargs.get("text_prompt_weight", self.text_prompt_weight)
        self.auto_prompt_weight = kwargs.get("auto_prompt_weight", self.auto_prompt_weight)
        self.prompt_prefix = kwargs.get("prompt_prefix", self.prompt_prefix)
        self.prompt_suffix = kwargs.get("prompt_suffix", self.prompt_suffix)
        self.negative_prompt_prefix = kwargs.get("negative_prompt_prefix", self.negative_prompt_prefix)
        self.negative_prompt_suffix = kwargs.get("negative_prompt_suffix", self.negative_prompt_suffix)
        self.negative_text_prompt_weight = kwargs.get("negative_text_prompt_weight", self.negative_text_prompt_weight)
        self.negative_auto_prompt_weight = kwargs.get("negative_auto_prompt_weight", self.negative_auto_prompt_weight)
        self.weighted_variables = kwargs.get("weighted_variables", self.weighted_variables)
        self.seed = kwargs.get("seed", self.seed)
        self.category = kwargs.get("category", self.category)
        self.image_genre = kwargs.get("image_genre", self.image_genre)
        self.image_color = kwargs.get("image_color", self.image_color)
        self.image_style = kwargs.get("image_style", self.image_style)
        self.advanced = kwargs.get("advanced", self.advanced)
        self.is_deterministic = kwargs.get("is_deterministic", False)
        self.is_batch = kwargs.get("is_batch", False)
        self.batch_size = kwargs.get("batch_size", 1)
        self.deterministic_style = kwargs.get("deterministic_style")

        random.seed(self.seed)

        if self.use_prompt_builder:

            category = self.category
            while category == "Random":
                category = random.choice(self.categories)

            image_genre = self.image_genre
            while image_genre == "Random":
                image_genre = random.choice(self.genres)

            image_color = self.image_color
            while image_color == "Random":
                image_color = random.choice(self.colors)

            image_style = self.image_style
            while image_style == "Random":
                image_style = random.choice(self.styles)

            weighted_variables = json.loads(self.weighted_variables) if not isinstance(self.weighted_variables, dict) else self.weighted_variables
            if category in weighted_variables:
                weighted_variables = weighted_variables[category]
            else:
                weighted_variables = {}

            variables = self.filter_variables(category, image_genre, image_color, image_style)
            if not self.advanced:
                generated_prompt = self.get_basic_prompt_by_category(category, "standard")
            else:
                generated_prompt = BuildPrompt.build_prompt(
                    conditionals=self.get_builder_by_category(category),
                    vars=variables,
                    category=category
                )

                # clean the generated_prompt before parsing
                generated_prompt = generated_prompt.strip()
                generated_prompt.replace("( ", "(")

            prefix = f"{self.prompt_prefix}, " if self.prompt_prefix != "" else ""
            suffix = f", {self.prompt_suffix}" if self.prompt_suffix != "" else ""

            # build the description of the image
            image_genre = None if self.image_genre == "" else self.image_genre
            image_style = None if self.image_style == "" else self.image_style
            image_color = None if self.image_color == "" else self.image_color
            description = ""
            if image_genre:
                description = "(A $composition_genre"
                if image_style:
                    description += " ($composition_style)++)+++"
                else:
                    description += ")++++"
            elif image_style:
                description += "(A $composition_style)+++"
            if image_color:
                if description != "":
                    description += f" with "
                description += "($composition_color colors)++++"
            description.strip()
            if description != "":
                description = f"({description}) of "

            generated_prompt = f"{prefix}{description}({generated_prompt})+{suffix}"

            # build the negative prompt
            prefix = f"{self.negative_prompt_prefix}, " if self.negative_prompt_prefix != "" else ""
            suffix = f", {self.negative_prompt_suffix}" if self.negative_prompt_suffix != "" else ""
            generated_negative_prompt = self.negative_prompt(category, image_style)
            generated_negative_prompt = f"{prefix} {generated_negative_prompt} {suffix}"

            # process the prompts
            prompt, negative_prompt = PromptParser.parse(
                prompt=self.current_prompt,
                negative_prompt=self.current_negative_prompt,
                generated_prompt=generated_prompt,
                generated_negative_prompt=generated_negative_prompt,
                text_weight=self.text_prompt_weight,
                auto_weight=self.auto_prompt_weight,
                negative_text_weight=self.negative_text_prompt_weight,
                negative_auto_weight=self.negative_auto_prompt_weight,
                variables=variables,
                weights=weighted_variables,
                seed=self.seed,
                deterministic_style=self.deterministic_style)
        else:
            prompt = self.current_prompt
            negative_prompt = self.current_negative_prompt
        if self.is_deterministic:
            prompt, negative_prompt = self.process_deterministic_prompt(prompt, negative_prompt, self.deterministic_style)
        elif self.is_batch:
            prompt, negative_prompt = self.process_batch_prompts(prompt, negative_prompt)

        return prompt, negative_prompt

    def process_deterministic_prompt(self, current_prompt, negative_prompt, deterministic_style):
        print("process_deterministic_prompt", deterministic_style)
        if isinstance(current_prompt, list):
            prompt = current_prompt[0]
        else:
            prompt = current_prompt
        prompt_list = [prompt]
        for _n in range(1, self.batch_size):
            if deterministic_style == "color":
                word = f"{PromptParser.random_color()} color"
            else:
                word = PromptParser.random_word()
            prompt_list.append(f"{prompt}, {word}")
        if isinstance(negative_prompt, list):
            negative_prompt = negative_prompt[0]
        negative_prompt = [
            f"{negative_prompt}" for _n in range(self.batch_size)
        ]
        return prompt_list, negative_prompt

    def process_batch_prompts(self, prompt, negative_prompt):
        if isinstance(prompt, list):
            prompt = prompt[0]
        prompt = [
            prompt for _n in range(self.batch_size)
        ]
        negative_prompt = [
            negative_prompt for _n in range(self.batch_size)
        ]
        return prompt, negative_prompt

    def available_prompts_by_category(self, category):
        return self.data["categories"][category]["prompts"].keys()

    def available_variables_by_category(self, category):
        return self.data["categories"][category]["variables"].keys()

    def variable_weights_by_category(self, category, variable):
        print("variable weights by category", category, variable)
        return self.data["categories"][category]["weights"][variable]

    def variable_values_by_category(self, category, variable):
        return self.data["categories"][category]["variables"][variable]

    def set_variable_values_by_category(self, category, variable, values):
        self.data["categories"][category]["variables"][variable] = values

    def prepare_variables(self, category, genre, color, style):
        variables = self.load_variables(category)
        variables = self.filter_composition_variables(genre, color, style, variables)
        return variables

    def get_basic_prompt_by_category(self, category, prompt_type):
        return ""

    def get_builder_by_category(self, category):
        return self.data["categories"][category]["builder"]

    def negative_prompt(self, category, image_style):
        negative_prompt_style_prefix = ""
        for style_category in self.style_categories():
            if image_style in self.styles_by_style_category(style_category):
                negative_prompt_style_prefix = self.negative_prompt_style_by_style_category(style_category)
                break
        generated_negative_prompt = self.negative_prompt_by_category(category)
        generated_negative_prompt = f"{negative_prompt_style_prefix} {generated_negative_prompt}"
        return generated_negative_prompt

    def negative_prompt_by_category(self, category):
        return self.data["categories"][category]["negative_prompt"]

    def negative_prompt_style_by_style_category(self, style_category):
        return self.data["styles"][style_category]["negative_prompt"]

    def style_categories(self):
        return self.data["styles"].keys()

    def styles_by_style_category(self, style_category):
        return self.data["styles"][style_category]["styles"]

    def filter_variables(self, category, genre, color, style):
        variables = self.prepare_variables(category, genre, color, style)

        weighted_variables = json.loads(self.weighted_variables) if not isinstance(self.weighted_variables, dict) else self.weighted_variables

        filtered_variables = {}

        if category == "Random":
            filtered_variables["composition_category"] = variables["composition_category"]
        elif category != "" and category is not None:
            filtered_variables["composition_category"] = [category]

        if genre == "Random":
            filtered_variables["composition_genre"] = variables["composition_genre"]
        elif genre != "" and genre is not None:
            filtered_variables["composition_genre"] = [genre]

        if color == "Random":
            filtered_variables["composition_color"] = variables["composition_color"]
        elif color != "" and color is not None:
            filtered_variables["composition_color"] = [color]

        if style == "Random":
            filtered_variables["composition_style"] = variables["composition_style"]
        elif style != "" and style is not None:
            filtered_variables["composition_style"] = [style]
        if category in weighted_variables:
            weighted_variables = weighted_variables[category]
            for variable in weighted_variables.keys():
                if variable in variables:
                    try:
                        value = weighted_variables[variable]["value"]
                    except KeyError:
                        value = ""
                    if value == "" or value is None:
                        continue
                    if value == "Random":
                        filtered_variables[variable] = variables[variable]
                    else:
                        filtered_variables[variable] = [value]
                    if variable == "gender":
                        filtered_variables["male_name"] = variables["male_name"] if "male_name" in variables else ""
                        filtered_variables["female_name"] = variables["female_name"] if "female_name" in variables else ""
        return filtered_variables

    def load_variables(self, category):
        """
        Loads the variables for the selected category.
        :return:
        """
        return {
            **self.prompt_variables.copy(),
            **self.data["categories"][category]["variables"].copy()
        }

    def filter_composition_variables(self, genre, color, style, variables):
        if genre not in ["", "Random"]:
            variables["composition_genre"] = [genre]
        if color not in ["", "Random"]:
            variables["composition_color"] = [color]
        if style not in ["", "Random"]:
            variables["composition_style"] = [style]
        return variables

    def build_prompt_options(self, prompt_id, builder=None, prompt_options=None, next_id=None):
        if builder is None:
            builder = []
        if prompt_options is None:
            session = get_session()
            prompt_options = session.query(PromptOption).filter_by(
                prompt_id=prompt_id
            ).all()
        for prompt_option in prompt_options:
            if next_id and next_id != prompt_option.id:
                continue

            options = dict(
                text=prompt_option.text,
            )
            if prompt_option.cond != "":
                options["cond"] = prompt_option.cond.split(",")
            if prompt_option.else_cond != "":
                options["else"] = prompt_option.else_cond
            if prompt_option.next_cond_id is not None and prompt_option.next_cond is not None:
                print("NEXT:", prompt_option.next_cond_id)
                options["next"] = self.build_prompt_options(
                    prompt_id=prompt_id,
                    builder=[],
                    prompt_options=prompt_options,
                    next_id=prompt_option.next_cond_id
                )
            builder.append(options)
        return builder

    def prepare_data(self, prompt_id):
        session = get_session()

        data = dict(
            categories=dict(),
            styles=dict(),
            extra_variables=dict(),
        )
        style_categories = session.query(PromptStyleCategory).all()
        for cat in style_categories:
            styles = session.query(PromptStyle).filter_by(
                style_category_id=cat.id
            ).all()
            data["styles"][cat.name] = dict(
                styles=[style.name for style in styles],
                negative_prompt=cat.negative_prompt
            )

        prompt_categories = session.query(PromptCategory).all()
        variable_categories = session.query(PromptVariableCategory).all()
        prompt_options = self.build_prompt_options(prompt_id)
        for prompt_category in prompt_categories:
            data["categories"][prompt_category.name] = dict(
                weights=dict(),
                variables=dict(),
                builder=prompt_options,
                negative_prompt=prompt_category.negative_prompt
            )
            for variable_category in variable_categories:
                variables = session.query(PromptVariable).filter_by(
                    prompt_category_id=prompt_category.id
                ).all()
                weights = session.query(PromptVariableCategoryWeight).filter_by(
                    prompt_category_id=prompt_category.id
                ).all()
                for variable in variables:
                    if variable.variable_category_id == variable_category.id:
                        if variable_category.name not in data["categories"][prompt_category.name]["variables"]:
                            data["categories"][prompt_category.name]["variables"][variable_category.name] = []
                        data["categories"][prompt_category.name]["variables"][variable_category.name].append(variable.value)
                for variable_weight in weights:
                    if variable_weight.variable_category_id == variable_category.id:
                        data["categories"][prompt_category.name]["weights"][variable_category.name] = variable_weight.weight

        self.data = data

        self.prompt_variables = self.data["extra_variables"]
        self.prompt_variables["age"] = [str(n) for n in range(18, 100)]

        self.set_variables_by_name("composition_color")
        self.set_variables_by_name("composition_style")
        self.set_variables_by_name("composition_category")
        self.set_variables_by_name("composition_genre")

        self.genres = self.prompt_variables["composition_genre"]
        self.styles = self.prompt_variables["composition_style"]
        self.colors = self.prompt_variables["composition_color"]
        self.categories = self.prompt_variables["composition_category"]

        with open("test.json", "w") as f:
            json.dump(self.data, f)
    
    def set_variables_by_name(self, name):
        session = get_session()
        composition_genre = session.query(PromptVariableCategory).filter_by(name=name).first()
        variables = session.query(PromptVariable).filter_by(variable_category_id=composition_genre.id).all()
        values = [variable.value for variable in variables]
        values.sort()
        self.prompt_variables[name] = ["Random"] + values
