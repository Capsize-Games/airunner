import unittest
from airunner.aihandler.llm.agent import ExternalConditionStoppingCriteria


class TestExternalConditionStoppingCriteria(unittest.TestCase):
    def setUp(self):
        self.condition = lambda: True
        self.criteria = ExternalConditionStoppingCriteria(self.condition)

    def test_init(self):
        self.assertEqual(self.criteria.external_condition_callable, self.condition)

    def test_call(self):
        self.assertTrue(self.criteria(None, None))

    def test_call_with_false_condition(self):
        self.criteria.external_condition_callable = lambda: False
        self.assertFalse(self.criteria(None, None))


if __name__ == '__main__':
    unittest.main()
