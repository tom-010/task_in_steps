
class Step:

    def run(self, config):
        raise NotImplementedError()

    def can_skip(self, config):
        return False

    def __call__(self, config):
        name = self.name if hasattr(self, 'name') else self.__name__
        print()
        print(f'=== {name} ==================')
        res = True
        message = 'done'
        if not self.can_skip(config):
            res = self.run(config)
            message = 'ok' if res else 'error'

        print(f'----{"-" * len(name)}-------------------')

        print(message)

        print(f'===={"=" * len(name)}===================')
        print()
        return res

def run_steps(config, steps):
    for step in steps:
        res = step(config)
        if not res:
            exit(1)