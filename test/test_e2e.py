from unittest import TestCase

from task_in_steps.task_in_steps import Step, run_steps

expected_e2e_output = '''
=== MyStep ==================
-----------------------------
done
=============================


=== MyStep ==================
Step output
-----------------------------
ok
=============================

'''

class TestE2E(TestCase):

    def test_e2e(self):
        config = None
        outputter=TestE2E.Outputter()
        run_steps(config, [
            TestE2E.MyStep(can_skip=True, outputter=outputter),
            TestE2E.MyStep(can_skip=False, outputter=outputter)
        ])
        result = outputter.content
        print(result)
        self.assertEqual(expected_e2e_output, result)

    class MyStep(Step):
        def __init__(self, can_skip, outputter):
            super().__init__(outputter=outputter)
            self._can_skip = can_skip
        
        def run(self, config):
            self.print('Step output')
            return True

        def can_skip(self, config):
            return self._can_skip

    class Outputter:
        def __init__(self):
            self.content = ''
        def __call__(self, *args):
            self.content += (' '.join(args)) + '\n'
