from dataclasses import dataclass


@dataclass
class CCLTraceback:
    position: tuple[int, int]
    line: str


class CCLParseError(Exception):
    def __init__(self, *args: object, traceback: CCLTraceback):
        super().__init__(*args)
        self.traceback = traceback


class CCLRuntimeError(Exception):
    def __init__(self, *args: object, traceback: CCLTraceback):
        super().__init__(*args)
        self.traceback = traceback


class CCLExit(Exception):
    pass
