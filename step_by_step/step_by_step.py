
class Step:

    def run(self, config):
        raise NotImplementedError()

    def can_skip(self, config):
        return False

    ## 

    def __init__(self, outputter=None):
        self.print = outputter or print

    def __call__(self, config):
        self._print_opening(self._my_name)
        status, res = self._execute(config)
        self._print_closing(self._my_name, status)
        return res
    
    ## 

    def _execute(self, config):
        status = 'done'
        res = True
        if not self.can_skip(config):
            res = self.run(config)
            status = 'ok' if res else 'error'
        return status, res

    

    def _print_opening(self, name):
        self.print()
        self.print(f'=== {name} ==================')

    def _print_closing(self, name, status):
        self.print(f'----{"-" * len(name)}-------------------')
        self.print(status)
        self.print(f'===={"=" * len(name)}===================')
        self.print()

    @property
    def _my_name(self):
        return self.name if hasattr(self, 'name') else self.__class__.__name__

def run_steps(config, steps):
    for step in steps:
        res = step(config)
        if not res:
            return False
    return True