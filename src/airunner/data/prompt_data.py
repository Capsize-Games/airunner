import json
import random

from aihandler.prompt_parser import PromptParser
from airunner.build_prompt import BuildPrompt


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

    def __init__(self, file_name=""):
        self.prepare_data(file_name=file_name)

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

        if category in self.weighted_variables:
            weighted_variables = self.weighted_variables[category]
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
        generated_prompt = f"{prefix}($composition_genre, $composition_color, ($composition_style)++) {generated_prompt}{suffix}"

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
            seed=self.seed)

        return prompt, negative_prompt

    def available_prompts_by_category(self, category):
        return self.data["categories"][category]["prompts"].keys()

    def available_variables_by_category(self, category):
        return self.data["categories"][category]["variables"].keys()

    def variable_weights_by_category(self, category, variable):
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
        return self.data["categories"][category]["prompts"][prompt_type]

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

        weighted_variables = self.weighted_variables
        if category in weighted_variables:
            weighted_variables = weighted_variables[category]
            for variable in weighted_variables.keys():
                if variable in variables:
                    value = weighted_variables[variable]["value"]
                    if value == "":
                        del variables[variable]
                    elif value != "Random":
                        variables[variable] = [value]
        return variables

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

    def prepare_genres(self):
        self.genres = self.prompt_variables["composition_genre"]
        self.genres.sort()
        self.genres = ["Random"] + self.prompt_variables["composition_genre"]

    def prepare_colors(self):
        self.colors = self.prompt_variables["composition_color"]
        self.colors.sort()
        self.colors = ["Random"] + self.prompt_variables["composition_color"]

    def prepare_styles(self):
        self.styles = self.prompt_variables["composition_style"]
        self.styles.sort()
        self.styles = ["Random"] + self.prompt_variables["composition_style"]

    def prepare_categories(self):
        self.categories = self.prompt_variables["composition_category"]
        self.categories.sort()
        self.categories = ["Random"] + self.prompt_variables["composition_category"]

    def prepare_data(self, file_name):
        self.load_data(file_name)
        self.prompt_variables = self.data["extra_variables"]
        self.prompt_variables["age"] = [str(n) for n in range(18, 100)]
        styles = []
        for style_category in self.data["styles"].keys():
            styles += self.data["styles"][style_category]["styles"]
        categories = list(self.data["categories"].keys())
        self.prompt_variables["composition_style"] = styles
        self.prompt_variables["composition_category"] = categories
        self.prepare_genres()
        self.prepare_styles()
        self.prepare_colors()
        self.prepare_categories()

    def load_data(self, file_name):
        file = f"data/{file_name}.json"
        with open(file, "r") as f:
            data = json.load(f)
            self.data = data
