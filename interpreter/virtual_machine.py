from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Self


@dataclass
class Cell:
    """
    Class that represents values on the stack.
    By default, each cell holds 2 byte signed number [-32768, 32767].
    Overflow is allowed, and results in jumping to the other sign (e.g -32769 jumps to 32767).

    NOTE: Overflowing only supposed to work when going out of boundary once (e.g. adding 32767 to 32767),
    due to it being impossible to add / subtract numbers higher that min/max value at runtime.

    ### List of allowed operations:
    - `Cell` + `int | Cell`
    - `Cell` += `int | Cell`
    - `Cell` - `int | Cell`
    - `Cell` -= `int | Cell`
    - `Cell` == `int | Cell`
    - `Cell` > `int | Cell`
    - `Cell` < `int | Cell`
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
        """
        Used in operator dunders.
        Checks if `other` has a valid type: either `Cell` or `int`.
        Raises `TypeError` if type is incorrect.
        """
        allowed_types = int, Cell
        if not isinstance(other, allowed_types):
            other_type = type(other).__name__
            raise TypeError(f"Operation '{operation}' is not supported between 'Cell' and '{other_type}'")

    def get_other_value(self, other: int | Cell) -> int:
        """
        Used in operator dunders.
        If `other` is a `Cell`, returns `Cell.value`, otherwise returns `other`.
        """
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

    def __gt__(self, other: int | Cell) -> bool:
        self.check_other_type('>', other)
        return self.value > self.get_other_value(other)

    def __lt__(self, other: int | Cell) -> bool:
        self.check_other_type('<', other)
        return self.value < self.get_other_value(other)


@dataclass
class Stack:
    """
    Class that represents a stack of cells.

    NOTE: attributes `size` and `top` are not meant to be modified:
    `Stack.size` replaces `len(Stack)`, `Stack.top` replaces `Stack.cells[-1]`.

    ### Attributes:
    - `Stack.size`: Amount of cells on the stack.
    - `Stack.top`: Top cell on the stack. Returns None if stack is empty.

    ### Methods:
    - `Stack.push(Cell)`: Appends a new cell to the top of the stack.
    - `Stack.pop()`: Deletes and returns the top cell on the stack.
    - `Stack.reverse_full()`: Reverses the entire stack.
    - `Stack.reverse(Cell)`: Reverses `Cell.value` top elements of the stack.
    """
    cells: list[Cell] = field(default_factory=list)
    size: int = field(default=0, init=False)
    top: Cell | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.size = len(self.cells)

    def __repr__(self) -> str:
        return '\n'.join([str(cell) for cell in self.cells[::-1]])

    def __getattribute__(self, name: str) -> Any:
        if name == 'top':
            return self.cells[-1] if self.cells else None
        else:
            return object.__getattribute__(self, name)

    def push(self, cell: Cell) -> None:
        """
        Appends provided `Cell` object to the top of the stack.
        """
        self.cells.append(cell)
        self.size += 1

    def pop(self) -> Cell:
        """
        Pops top `Cell` from the stack and returns it.
        `IndexError` is raised if stack is currently empty.
        """
        cell = self.cells.pop()
        self.size -= 1
        return cell

    def reverse_full(self) -> None:
        """
        Reverses the entire stack in-place.
        """
        self.cells.reverse()

    def reverse(self, cell: Cell) -> None:
        """
        Reverses `Cell.value` amount of top elements of the stack in-place.
        If `Cell.value` is higher than `Stack.size` or lower than 0, `ValueError` is raised.
        """
        if cell > self.size:
            raise ValueError(f"Cell's value ({cell.value}) exceeds size of the stack ({self.size})")
        if cell < 0:
            raise ValueError(f"Cell's value ({cell.value}) must not be less than 0.")
        if cell < 2:
            return
        reverse_index = self.size - cell.value
        self.cells = self.cells[:reverse_index] + self.cells[reverse_index:][::-1]
