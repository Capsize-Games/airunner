import unittest

from airunner.handlers.stablediffusion import PromptWeightBridge


class TestPromptWeightConvert(unittest.TestCase):
    def test_simple(self):
        prompt = "Example (a GHI:1.4)"
        expected_prompt = "Example (a GHI)1.4"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

    def test_use_case_a(self):
        prompt = "Example (ABC): 1.23 XYZ (DEF) (GHI:1.4)"
        expected_prompt = "Example (ABC)1.1: 1.23 XYZ (DEF)1.1 (GHI)1.4"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

    def test_use_case_b(self):
        prompt = "(a dog:0.5) and a cat"
        expected_prompt = "(a dog)0.5 and a cat"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

    def test_use_case_c(self):
        prompt = "A perfect photo of a woman wearing a respirator wandering through the (toxic wasteland:1.3)"
        expected_prompt = "A perfect photo of a woman wearing a respirator wandering through the (toxic wasteland)1.3"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

    def test_use_case_d(self):
        prompt = "(worst quality:0.8), fantasy, cartoon, halftone print, (cinematic:1.2), verybadimagenegative_v1.3, " \
                 "easynegative, (surreal:0.8), (modernism:0.8), (art deco:0.8), (art nouveau:0.8)"
        expected_prompt = "(worst quality)0.8, fantasy, cartoon, halftone print, (cinematic)1.2, " \
                          "verybadimagenegative_v1.3, easynegative, (surreal)0.8, (modernism)0.8, (art deco)0.8, " \
                          "(art nouveau)0.8"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

    def test_convert_basic_parentheses(self):
        prompt = "(a hammer) and a cat in a car"
        expected_prompt = "(a hammer)1.1 and a cat in a car"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "a foo and (a cat) in a car"
        expected_prompt = "a foo and (a cat)1.1 in a car"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "(a bar) and (a cat) in a car"
        expected_prompt = "(a bar)1.1 and (a cat)1.1 in a car"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "(a baz) and (a cat) in (a car)"
        expected_prompt = "(a baz)1.1 and (a cat)1.1 in (a car)1.1"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "((a car)) and a cat"
        expected_prompt = "(a car)1.21 and a cat"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "(((((((((((a car))))))))))) and a cat"
        expected_prompt = "(a car)1.4 and a cat"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "(((((((((((a car))))))))))) and (((a cat)))"
        expected_prompt = "(a car)1.4 and (a cat)1.33"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

    def test_convert_basic_brackets(self):
        prompt = "[a hammer] and a cat in a car"
        expected_prompt = "(a hammer)0.9 and a cat in a car"
        self.assertEqual(PromptWeightBridge.convert_basic_brackets(prompt), expected_prompt)

        prompt = "a foo and [a cat] in a car"
        expected_prompt = "a foo and (a cat)0.9 in a car"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "[a bar] and [a cat] in a car"
        expected_prompt = "(a bar)0.9 and (a cat)0.9 in a car"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "[a baz] and [a cat] in [a car]"
        expected_prompt = "(a baz)0.9 and (a cat)0.9 in (a car)0.9"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "[[a car]] and a cat"
        expected_prompt = "(a car)0.79 and a cat"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "[[[[[[[[[[[a car]]]]]]]]]]] and a cat"
        expected_prompt = "(a car)0.0 and a cat"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "[[[[[[[[[[[a car]]]]]]]]]]] and [[[a cat]]]"
        expected_prompt = "(a car)0.0 and (a cat)0.67"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

    def test_convert_prompt_with_weight_value(self):
        prompt = "(a bird:0.5) and a plane"
        expected_prompt = "(a bird)0.5 and a plane"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "a dog and (a cat:0.6)"
        expected_prompt = "a dog and (a cat)0.6"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "(a boat:0.5) and (a ship:0.6)"
        expected_prompt = "(a boat)0.5 and (a ship)0.6"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "(a man:0.5) and a woman"
        expected_prompt = "(a man)0.5 and a woman"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

    def test_compel_prompt_weight(self):
        prompt = "(a asdf)1.4 and a cat in a car"
        expected_prompt = "(a asdf)1.4 and a cat in a car"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "a man (eating an apple)++++"
        expected_prompt = "a man (eating an apple)++++"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "a man (eating fruit)+"
        expected_prompt = "a man (eating fruit)+"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "a man (eating a bannana)----"
        expected_prompt = "a man (eating a bannana)----"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "a man (eating bread)-"
        expected_prompt = "a man (eating bread)-"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = '("blue sphere", "red cube").blend(0.25,0.75)'
        expected_prompt = prompt
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

    def test_mixed_prompt(self):
        prompt = "a man (drinking (water))0.5"
        expected_prompt = "a man (drinking (water)1.1)0.5"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "a man (drinking ((milk)))0.5"
        expected_prompt = "a man (drinking (milk)1.21)0.5"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "a man (drinking+ ((juice)))0.5"
        expected_prompt = "a man (drinking+ (juice)1.21)0.5"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "a man ((drinking:1.1) ((beer)))0.5"
        expected_prompt = "a man ((drinking)1.1 (beer)1.21)0.5"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "a fox (drinking) water in a [bar] from (the country) of [canada]"
        expected_prompt = "a fox (drinking)1.1 water in a (bar)0.9 from (the country)1.1 of (canada)0.9"
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

    def test_blend_conversion(self):
        prompt = "A [frog:turtle:0.1] on a leaf in the forest"
        expected_prompt = 'A ("frog", "turtle").blend(0.1, 0.9) on a leaf in the forest'
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "A [frog:turtle:0.5] on a leaf in the forest"
        expected_prompt = 'A ("frog", "turtle").blend(0.5, 0.5) on a leaf in the forest'
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)

        prompt = "A (frog:turtle:0.1) on a leaf in the forest"
        expected_prompt = 'A ("frog", "turtle").blend(0.9, 0.1) on a leaf in the forest'
        self.assertEqual(PromptWeightBridge.convert(prompt), expected_prompt)
