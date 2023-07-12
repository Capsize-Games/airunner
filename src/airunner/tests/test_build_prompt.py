import json
import unittest

from airunner.build_prompt import BuildPrompt


class TestBuildPrompt(unittest.TestCase):
    def setUp(self):
        with open("data/prompts.json") as f:
            self.data = json.load(f)

    def test_no_variables(self):
        builder = self.data["categories"]["person"]["builder"]
        self.assertEqual(
            BuildPrompt.build_prompt(
                conditionals=builder,
                image_style="contemporary",
                vars={},
                category="person"
            ),
            "($style, $color, (contemporary)++), A person ."
        )

    def test_ethnicity(self):
        builder = self.data["categories"]["person"]["builder"]
        self.assertEqual(
            BuildPrompt.build_prompt(
                conditionals=builder,
                image_style="contemporary",
                vars={
                    "ethnicity": ["asdf"]
                },
                category="person"
            ),
            "($style, $color, (contemporary)++), A $ethnicity ."
        )

    def test_gender(self):
        builder = self.data["categories"]["person"]["builder"]
        self.assertEqual(
            BuildPrompt.build_prompt(
                conditionals=builder,
                image_style="contemporary",
                vars={
                    "gender": ["asdf"]
                },
                category="person"
            ),
            "($style, $color, (contemporary)++), A $gender person named $$gender_name ."
        )

    def test_no_gender_with_age(self):
        builder = self.data["categories"]["person"]["builder"]
        self.assertEqual(
            BuildPrompt.build_prompt(
                conditionals=builder,
                image_style="contemporary",
                vars={
                    "age": ["asdf"]
                },
                category="person"
            ),
            "($style, $color, (contemporary)++), A person . The person is $age"
        )

    def test_hair_length_and_color(self):
        builder = self.data["categories"]["person"]["builder"]
        self.assertEqual(
            BuildPrompt.build_prompt(
                conditionals=builder,
                image_style="contemporary",
                vars={
                    "hair_length": ["asdf"],
                    "hair_color": ["asdf"]
                },
                category="person"
            ),
            "($style, $color, (contemporary)++), A person . ($hair_length $hair_color hair.)"
        )

    def test_gender_body_type(self):
        builder = self.data["categories"]["person"]["builder"]
        self.assertEqual(
            BuildPrompt.build_prompt(
                conditionals=builder,
                image_style="contemporary",
                vars={
                    "gender": ["asdf"],
                    "body_type": ["asdf"],
                },
                category="person"
            ),
            "($style, $color, (contemporary)++), A $gender person named $$gender_name . $$gender_name has a ($body_type body-type),"
        )

    def test_body_type(self):
        builder = self.data["categories"]["person"]["builder"]
        self.assertEqual(
            BuildPrompt.build_prompt(
                conditionals=builder,
                image_style="contemporary",
                vars={
                    "body_type": ["asdf"],
                },
                category="person"
            ),
            "($style, $color, (contemporary)++), A person . The person has a ($body_type body-type),"
        )

    def test_gender_wearing(self):
        builder = self.data["categories"]["person"]["builder"]
        self.assertEqual(
            BuildPrompt.build_prompt(
                conditionals=builder,
                image_style="contemporary",
                vars={
                    "shoes": ["asdf"],
                },
                category="person"
            ),
            "($style, $color, (contemporary)++), A person . the person (wearing $shoes),"
        )

    def test_next(self):
        builder = self.data["categories"]["animal"]["builder"]
        self.assertEqual(
            BuildPrompt.build_prompt(
                conditionals=builder,
                image_style="contemporary",
                vars={
                    "animal": ["asdf"],
                    "emotion": ["asdf"],
                },
                category="person"
            ),
            "($style, $color, (contemporary)++), A $animal , captured in motion. The $animal looks $emotion. vibrant and lively, natural composition, perfect lighting, an amazing sight."
        )