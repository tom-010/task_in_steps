from unittest import TestCase

from task_in_steps import Step

class TestStep(TestCase):

    def test_run_is_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            Step().run(None)

    def test_can_skip_per_default_false(self):
        self.assertFalse(Step().can_skip(None))

    def test_my_name_if_not_specified(self):
        self.assertEqual('StepWithoutName', self.StepWithoutName()._my_name)

    def test_my_name_if_specified(self):
        self.assertEqual('a name', self.StepWithName()._my_name)

    class StepWithoutName(Step):
        pass

    class StepWithName(Step):
        name = 'a name'