from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Self


@dataclass
class Cell:
    """
    Class that represents values on the stack.
    By default, each cell holds 2 byte signed number [-32 768, 32 767].
    Overflow is allowed, and results in jumping to the other sign (e.g -32769 jumps to 32767).

    NOTE: Overflowing only supposed to work when going out of boundary once (e.g. adding 32767 to 32767),
    due to it being impossible to add / subtract numbers higher that min/max value at runtime.

    ### List of allowed operations:
    - `Cell` + `int | Cell`
    - `Cell` += `int | Cell`
    - `Cell` - `int | Cell`
    - `Cell` -= `int | Cell`
    - `Cell` == `int | Cell`
    """
    value: int
    min_value: int = -32_768
    max_value: int = 32_767

    def __repr__(self) -> str:
        return f'[ {self.value} ]'

    def __setattr__(self, name: str, value: int) -> None:
        if name == 'value':
            if value > self.max_value: value = self.min_value + (value - self.max_value - 1)
            elif value < self.min_value: value = self.max_value + (value - self.min_value + 1)
        self.__dict__[name] = value

    def check_other_type(self, operation: str, other: Any) -> None:
        allowed_types = int, Cell
        if not isinstance(other, allowed_types):
            other_type = type(other).__name__
            raise TypeError(f"Operation '{operation}' is not supported between 'Cell' and '{other_type}'")

    def get_other_value(self, other: int | Cell) -> int:
        if isinstance(other, Cell):
            return other.value
        else:
            return other

    def __add__(self, other: int | Cell) -> Self:
        self.check_other_type('+', other)
        self.value += self.get_other_value(other)
        return self

    def __iadd__(self, other: int | Cell) -> Self:
        self.check_other_type('+=', other)
        self.value += self.get_other_value(other)
        return self

    def __sub__(self, other: int | Cell) -> Self:
        self.check_other_type('-', other)
        self.value -= self.get_other_value(other)
        return self

    def __isub__(self, other: int | Cell) -> Self:
        self.check_other_type('-=', other)
        self.value -= self.get_other_value(other)
        return self

    def __eq__(self, other: int | Cell) -> bool:
        self.check_other_type('==', other)
        return self.value == self.get_other_value(other)
