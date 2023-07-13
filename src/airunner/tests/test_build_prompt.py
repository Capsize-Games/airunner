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
                vars={},
                category="person"
            ),
            "A person ."
        )

    def test_ethnicity(self):
        builder = self.data["categories"]["person"]["builder"]
        self.assertEqual(
            BuildPrompt.build_prompt(
                conditionals=builder,
                vars={
                    "ethnicity": ["asdf"]
                },
                category="person"
            ),
            "A $ethnicity ."
        )

    def test_gender(self):
        builder = self.data["categories"]["person"]["builder"]
        self.assertEqual(
            BuildPrompt.build_prompt(
                conditionals=builder,
                vars={
                    "gender": ["asdf"]
                },
                category="person"
            ),
            "A $gender person named $$gender_name ."
        )

    def test_no_gender_with_age(self):
        builder = self.data["categories"]["person"]["builder"]
        self.assertEqual(
            BuildPrompt.build_prompt(
                conditionals=builder,
                vars={
                    "age": ["asdf"]
                },
                category="person"
            ),
            "A person . The person is $age"
        )

    def test_hair_length_and_color(self):
        builder = self.data["categories"]["person"]["builder"]
        self.assertEqual(
            BuildPrompt.build_prompt(
                conditionals=builder,
                vars={
                    "hair_length": ["asdf"],
                    "hair_color": ["asdf"]
                },
                category="person"
            ),
            "A person . ($hair_length $hair_color hair.)"
        )

    def test_gender_body_type(self):
        builder = self.data["categories"]["person"]["builder"]
        self.assertEqual(
            BuildPrompt.build_prompt(
                conditionals=builder,
                vars={
                    "gender": ["asdf"],
                    "body_type": ["asdf"],
                },
                category="person"
            ),
            "A $gender person named $$gender_name . $$gender_name has a ($body_type body-type),"
        )

    def test_body_type(self):
        builder = self.data["categories"]["person"]["builder"]
        self.assertEqual(
            BuildPrompt.build_prompt(
                conditionals=builder,
                vars={
                    "body_type": ["asdf"],
                },
                category="person"
            ),
            "A person . The person has a ($body_type body-type),"
        )

    def test_gender_wearing(self):
        builder = self.data["categories"]["person"]["builder"]
        self.assertEqual(
            BuildPrompt.build_prompt(
                conditionals=builder,
                vars={
                    "shoes": ["asdf"],
                },
                category="person"
            ),
            "A person . the person (wearing $shoes),"
        )

    def test_next(self):
        builder = self.data["categories"]["animal"]["builder"]
        self.assertEqual(
            BuildPrompt.build_prompt(
                conditionals=builder,
                vars={
                    "animal": ["asdf"],
                    "emotion": ["asdf"],
                },
                category="person"
            ),
            "A $animal , captured in motion. The $animal looks $emotion. vibrant and lively, natural composition, perfect lighting, an amazing sight."
        )