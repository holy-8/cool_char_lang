from __future__ import annotations
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self


@dataclass
class Cell:
    """
    Class that represents values on the stack.
    By default, each cell holds 2 byte signed number [-32768, 32767].
    Overflow is allowed, and results in jumping to the other sign (e.g -32769 jumps to 32767).

    NOTE: Overflowing only supposed to work when going out of boundary once (e.g. adding 32767 to 32767),
    due to it being impossible to add / subtract numbers higher that min/max value at runtime.

    ### Attributes:
    - `Cell.digits`: length of `str(Cell.value)`. Not meant to be modified.

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
    digits: int = field(default=1, init=False)

    def __repr__(self) -> str:
        return f'[ {self.value} ]'

    def __getattribute__(self, name: str) -> Any:
        if name == 'digits':
            return len(f'{self.value}')
        else:
            return object.__getattribute__(self, name)

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
        width = max(cell.digits for cell in self.cells)
        return '\n'.join([
            f'[ {str(cell.value).center(width)} ]'
            for cell in self.cells
        ])

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


@dataclass
class VirtualMachine:
    stack: Stack = field(default_factory=Stack)
    global_vars: dict[str, Cell] = field(default_factory=dict)
    global_procedures: dict[str, Procedure] = field(default_factory=dict)
    call_stack: list[Procedure] = field(default_factory=list)

    def execute_next(self) -> None:
        if not self.call_stack:
            raise Exception(...)
        try:
            self.call_stack[-1].execute_next()
        except IndexError:
            self.call_stack.pop()


@dataclass
class Procedure:
    virtual_machine: VirtualMachine
    name: str = 'Main'
    local_vars: dict[str, Cell] = field(default_factory=dict)
    instruction_stack: list[Instruction] = field(default_factory=list)
    instruction_pointer: int = field(default=0)

    def execute_next(self) -> None:
        self.instruction_stack[self.instruction_pointer].execute()
        self.instruction_pointer += 1

    def get_local_var(self, name: str) -> Cell | None:
        if name not in self.local_vars or self.name == 'Main':
            return None
        else:
            return self.local_vars[name]

    def get_global_var(self, name: str) -> Cell | None:
        if name not in self.virtual_machine.global_vars:
            return None
        else:
            return self.virtual_machine.global_vars[name]

    def clone(self) -> Procedure:
        return Procedure(
            virtual_machine=self.virtual_machine,
            name=self.name,
            instruction_stack=deepcopy(self.instruction_stack),
            instruction_pointer=self.instruction_pointer
        )


@dataclass
class Traceback:
    file: Path
    procedure: Procedure
    line: int
    span: tuple[int, int]


@dataclass
class Instruction(ABC):
    procedure: Procedure
    traceback: Traceback
    parameter: str = '_'

    def __post_init__(self) -> None:
        self.global_stack = self.procedure.virtual_machine.stack

    def assert_stack_size(self, min_size: int) -> None:
        if self.global_stack.size < min_size:
            raise Exception(...)

    def assert_empty_parameter(self) -> None:
        if self.parameter == '_':
            raise Exception(...)

    def get_var(self, name: str) -> Cell:
        if local_var := self.procedure.get_local_var(name):
            return local_var
        elif global_var := self.procedure.get_global_var(name):
            return global_var
        else:
            raise Exception(...)

    @abstractmethod
    def execute(self) -> None:
        pass


class PushZero(Instruction):
    def execute(self) -> None:
        self.global_stack.push(Cell(0))


class Increment(Instruction):
    def execute(self) -> None:
        self.assert_stack_size(1)
        self.global_stack.top += 1


class Decrement(Instruction):
    def execute(self) -> None:
        self.assert_stack_size(1)
        self.global_stack.top -= 1


class Add(Instruction):
    def execute(self) -> None:
        self.assert_stack_size(2)
        prev_top = self.global_stack.pop()
        self.global_stack.top += prev_top


class Subtract(Instruction):
    def execute(self) -> None:
        self.assert_stack_size(2)
        prev_top = self.global_stack.pop()
        self.global_stack.top -= prev_top
