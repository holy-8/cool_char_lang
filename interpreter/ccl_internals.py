from __future__ import annotations
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from copy import copy, deepcopy
from enum import Enum, StrEnum
from click import getchar
from ccl_exceptions import CCLRuntimeError, CCLExit, CCLTraceback


class Cell:
    _value = 0
    _min = -32768
    _max = 32767
    def __init__(self, _value: int, /, *,
                 min_value: int = -32768,
                 max_value: int = 32767):
        self._value = _value
        self._min = min_value
        self._max = max_value

    def __setattr__(self, name, value):
        if name != '_value':
            self.__dict__[name] = value
            return

        if value > self._max:
            self.__dict__[name] = self._min + (value - self._max - 1)
        elif value < self._min:
            self.__dict__[name] = self._max - (abs(value) + self._min - 1)
        else:
            self.__dict__[name] = value

    def __repr__(self):
        return f'[ {self._value} ]'

    def __bool__(self):
        return True

    def __iadd__(self, other):
        if not isinstance(other, (type(self), int)):
            raise TypeError(f"Cannot use += between type '{type(self).__name__}' and type '{type(other).__name__}'")

        if isinstance(other, int):
            self._value += other
        else:
            self._value += other._value

        return self

    def __isub__(self, other):
        if not isinstance(other, (type(self), int)):
            raise TypeError(f"Cannot use -= between type '{type(self).__name__}' and type '{type(other).__name__}'")

        if isinstance(other, int):
            self._value -= other
        else:
            self._value -= other._value

        return self

    def __eq__(self, other):
        if not isinstance(other, (type(self), int)):
            raise TypeError(f"Cannot use == between type '{type(self).__name__}' and type '{type(other).__name__}'")

        if isinstance(other, int):
            return self._value == other
        else:
            return self._value == other._value


class Context(Enum):
    PROCEDURE = 0
    REPEAT = 1
    WHILE = 2


class KeyIgnore(StrEnum):
    F1 = '\x00;'
    F2 = '\x00<'
    F3 = '\x00='
    F4 = '\x00>'
    F5 = '\x00?'
    F6 = '\x00@'
    F7 = '\x00A'
    F8 = '\x00B'
    F9 = '\x00C'
    F10 = '\x00D'
    F11 = 'à\x85'
    F12 = 'à\x86'
    ESCAPE = '\x1b'
    BACKSPACE = '\x08'
    INSERT = 'àR'
    DELETE = 'àS'
    HOME = 'àG'
    PAGE_UP = 'àI'
    PAGE_DOWN = 'àQ'
    END = 'àO'
    ARROW_UP = 'àH'
    ARROW_DOWN = 'àP'
    ARROW_LEFT = 'àK'
    ARROW_RIGHT = 'àM'
    VSCODE_UP = '\x00H'
    VSCODE_DOWN = '\x00P'
    VSCODE_LEFT = '\x00K'
    VSCODE_RIGHT = '\x00M'


class Procedure:
    def __init__(self, name: str, global_namespace: MainProcedure):
        # Globals (imported from MainProcedure):
        self.stack = global_namespace.stack
        self.global_variables = global_namespace.global_variables
        self.defined_procedures = global_namespace.defined_procedures
        self.call_stack = global_namespace.call_stack
        self.stdout = global_namespace.stdout
        self.debug_mode = global_namespace.debug_mode
        # Locals:
        self.name = name
        self.local_variables: dict[str, Cell] | None = dict()
        self.instruction_stack: list[Instruction] = list()
        self.instruction_pointer: int = 0

    def __repr__(self) -> str:
        return f"<Procedure '{self.name}'>"

    def next_instruction(self):
        if self.debug_mode:
            print(f'[DEBUG]: {self} instruction_pointer = {self.instruction_pointer}')
        self.instruction_stack[self.instruction_pointer].execute()


class MainProcedure:
    # Globals:
    stack: list[Cell] = list()
    global_variables: dict[str, Cell] = dict()
    defined_procedures: dict[str, Procedure] = dict()
    call_stack: list[Procedure] = list()
    stdout: list[str] = list()
    debug_mode: bool = False
    # Locals:
    stdout_buffer: list[str] = list()
    instruction_stack: list[Instruction] = list()
    locals_stack: list[dict[str, Cell]] = list()
    instruction_pointer: int = 0

    def __repr__(self) -> str:
        return f"<Procedure 'MainProcedure'>"

    def next_instruction(self):
        if len(self.call_stack) > 0:
            try:
                procedure = self.call_stack[-1]
                instruction = procedure.instruction_stack[procedure.instruction_pointer]
                if isinstance(instruction, CallProcedure):
                    if instruction.name_parameter == procedure.name:
                        self.locals_stack.append(
                            deepcopy(procedure.local_variables)
                        )
                self.call_stack[-1].next_instruction()
            except CCLExit:
                self.call_stack[-1].local_variables.clear()
                self.call_stack.pop()
                if len(self.call_stack) > 0:
                    self.call_stack[-1].instruction_pointer += 1
                    if self.locals_stack:
                        self.call_stack[-1].local_variables.update(self.locals_stack.pop())
                        for instruction in self.call_stack[-1].instruction_stack:
                            instruction.namespace = self.call_stack[-1]
            return

        if self.debug_mode:
            print(f'[DEBUG]: {self} instruction_pointer = {self.instruction_pointer}')
        self.instruction_stack[self.instruction_pointer].execute()

    def print_stdout(self):
        if self.debug_mode:
            print('== OUTPUT ==')
            print(''.join(self.stdout))
            print('=' * 12)
        else:
            if self.stdout == self.stdout_buffer:
                return
            main_instruction = self.instruction_stack[self.instruction_pointer]
            if not self.call_stack and isinstance(main_instruction, (StdIn, ExitBlock, EndProcedure)):
                if isinstance(main_instruction, ExitBlock):
                    if main_instruction.context != Context.PROCEDURE:
                        return
                os.system('cls')
                print(''.join(self.stdout), end='')
                self.stdout_buffer = copy(self.stdout)
            if self.call_stack:
                procedure = self.call_stack[-1]
                procedure_instruction = procedure.instruction_stack[procedure.instruction_pointer]
                if isinstance(procedure_instruction, StdIn):
                    os.system('cls')
                    print(''.join(self.stdout), end='')
                    self.stdout_buffer = copy(self.stdout)

    def print_stack(self):
        print('-- STACK --')
        for cell in reversed(self.stack):
            print(cell)
        print()

    def print_variables(self):
        print('-- VARIABLES --')
        for name in self.global_variables:
            print(f'GLOBAL {name} = {self.global_variables[name]._value}')

        if len(self.call_stack) > 0:
            for name in self.call_stack[-1].local_variables:
                print(f'LOCAL {self.call_stack[-1].name}::{name} = {self.call_stack[-1].local_variables[name]._value}')
        print()

    def print_procedures(self):
        print('-- PROCEDURES --')
        for name in self.defined_procedures:
            print(f'{name}{{...}}')
        print()

    def debug(self):
        self.print_stdout()
        self.print_stack()
        self.print_variables()
        self.print_procedures()


@dataclass
class Instruction(ABC):
    namespace: MainProcedure | Procedure | None
    traceback: CCLTraceback

    def get_global_variable(self, name: str) -> Cell | None:
        if name not in self.namespace.global_variables:
            return None

        return self.namespace.global_variables[name]

    def get_local_variable(self, name: str) -> Cell | None:
        if not isinstance(self.namespace, Procedure):
            return None

        if name not in self.namespace.local_variables:
            return None

        return self.namespace.local_variables[name]

    def execute(self):
        self.callback()
        self.namespace.instruction_pointer += 1
        if self.namespace.debug_mode:
            print(f'[DEBUG]: Instruction.execute() {id(self.namespace) = }, {self.namespace.instruction_pointer = }')
            print()

    @abstractmethod
    def callback(self):
        pass


@dataclass
class DefineProcedure(Instruction):
    name_parameter: str
    instruction_stack: list[Instruction]

    def callback(self):
        procedure = Procedure(name=self.name_parameter, global_namespace=self.namespace)

        for instruction in deepcopy(self.instruction_stack):
            instruction.namespace = procedure
            procedure.instruction_stack.append(instruction)

        procedure.instruction_stack.append(
            EndProcedure(namespace=procedure, traceback=self.traceback)
        )

        self.namespace.defined_procedures[self.name_parameter] = procedure


@dataclass
class CallProcedure(Instruction):
    name_parameter: str

    def callback(self):
        if self.name_parameter is None:
            raise CCLRuntimeError(f"Instruction '@_': name must be provided and cannot be '_'", traceback=self.traceback)

        if self.name_parameter not in self.namespace.defined_procedures:
            raise CCLRuntimeError(f"Instruction '@{self.name_parameter}': procedure '{self.name_parameter}' is undefined", traceback=self.traceback)

        self.namespace.call_stack.append(
            copy(
                self.namespace.defined_procedures[self.name_parameter]
            )
        )
        for instruction in self.namespace.call_stack[-1].instruction_stack:
            instruction.namespace = self.namespace.call_stack[-1]

        if isinstance(self.namespace, Procedure):
            self.namespace.instruction_pointer -= 1


@dataclass
class PushZero(Instruction):
    def callback(self):
        self.namespace.stack.append(
            Cell(0)
        )


@dataclass
class Assign(Instruction):
    name_parameter: str | None

    def callback(self):
        if not self.namespace.stack:
            raise CCLRuntimeError("Instruction '=': cannot pop from an empty stack", traceback=self.traceback)

        value = self.namespace.stack.pop()

        if self.name_parameter is None:
            return

        if self.get_local_variable(self.name_parameter):
            self.namespace.local_variables[self.name_parameter] = value
            return

        self.namespace.global_variables[self.name_parameter] = value


@dataclass
class Delete(Instruction):
    name_parameter: str

    def callback(self):
        if self.name_parameter is None:
            raise CCLRuntimeError(f"Instruction '!_': name must be provided and cannot be '_'", traceback=self.traceback)

        if self.get_local_variable(self.name_parameter):
            self.namespace.local_variables.pop(self.name_parameter)
            return

        if self.get_global_variable(self.name_parameter):
            self.namespace.global_variables.pop(self.name_parameter)
            return

        raise CCLRuntimeError(f"Instruction '!{self.name_parameter}': variable '{self.name_parameter}' is undefined", traceback=self.traceback)


@dataclass
class CreateLocal(Instruction):
    name_parameter: str

    def callback(self):
        if self.name_parameter is None:
            raise CCLRuntimeError(f"Instruction '&_': name must be provided and cannot be '_'", traceback=self.traceback)

        if not isinstance(self.namespace, Procedure):
            raise CCLRuntimeError(f"Instruction '&{self.name_parameter}': cannot create local variable outside of procedure", traceback=self.traceback)

        self.namespace.local_variables[self.name_parameter] = Cell(0)


@dataclass
class PushVariable(Instruction):
    name_parameter: str

    def callback(self):
        if self.name_parameter is None:
            raise CCLRuntimeError(f"Instruction '$_': name must be provided and cannot be '_'", traceback=self.traceback)

        value = self.get_local_variable(self.name_parameter)
        if not value:
            value = self.get_global_variable(self.name_parameter)
        if not value:
            raise CCLRuntimeError(f"Instruction '${self.name_parameter}': variable '{self.name_parameter}' is undefined", traceback=self.traceback)
    
        self.namespace.stack.append(
            copy(value)
        )


@dataclass
class Add(Instruction):
    def callback(self):
        if not self.namespace.stack:
            raise CCLRuntimeError("Instruction '+': cannot add to an empty stack", traceback=self.traceback)

        self.namespace.stack[-1] += 1


@dataclass
class Subtract(Instruction):
    def callback(self):
        if not self.namespace.stack:
            raise CCLRuntimeError("Instruction '-': cannot subtract from an empty stack", traceback=self.traceback)

        self.namespace.stack[-1] -= 1


@dataclass
class PopAdd(Instruction):
    def callback(self):
        if len(self.namespace.stack) < 2:
            raise CCLRuntimeError(f"Instruction '*': not enough elements on the stack ({len(self.namespace.stack)}); at least 2 required", traceback=self.traceback)

        top_value = self.namespace.stack.pop()
        next_value = self.namespace.stack.pop()
        next_value += top_value

        self.namespace.stack.append(
            next_value
        )


@dataclass
class PopSubtract(Instruction):
    def callback(self):
        if len(self.namespace.stack) < 2:
            raise CCLRuntimeError(f"Instruction '~': not enough elements on the stack ({len(self.namespace.stack)}); at least 2 required", traceback=self.traceback)

        top_value = self.namespace.stack.pop()
        next_value = self.namespace.stack.pop()
        next_value -= top_value

        self.namespace.stack.append(
            next_value
        )


@dataclass
class Reverse(Instruction):
    name_parameter: str | None

    def callback(self):
        if not self.name_parameter:
            self.namespace.stack.reverse()
            return

        cell = self.get_local_variable(self.name_parameter)
        if not cell:
            cell = self.get_global_variable(self.name_parameter)
        if not cell:
            raise CCLRuntimeError(f"Instruction '%{self.name_parameter}': variable '{self.name_parameter}' is undefined", traceback=self.traceback)
        amount = cell._value

        if len(self.namespace.stack) < amount:
            raise CCLRuntimeError(f"Instruction '%{self.name_parameter}': parameter ('{self.name_parameter}' = {amount}) exceeds length of the stack ({len(self.namespace.stack)})", traceback=self.traceback)
        if amount < 1:
            raise CCLRuntimeError(f"Instruction '%{self.name_parameter}': parameter ('{self.name_parameter}' = {amount}) cannot be less than 1", traceback=self.traceback)


        top_reversed = self.namespace.stack[-amount:][::-1]
        bottom = self.namespace.stack[:-amount]

        self.namespace.stack.clear()
        self.namespace.stack.extend(bottom)
        self.namespace.stack.extend(top_reversed)


@dataclass
class StdOut(Instruction):
    name_parameter: str

    def callback(self):
        if self.name_parameter is None:
            raise CCLRuntimeError(f"Instruction '<_': name must be provided and cannot be '_'", traceback=self.traceback)

        cell = self.get_local_variable(self.name_parameter)
        if not cell:
            cell = self.get_global_variable(self.name_parameter)
        if not cell:
            raise CCLRuntimeError(f"Instruction '<{self.name_parameter}': variable '{self.name_parameter}' is undefined", traceback=self.traceback)
        char = cell._value

        if char not in range(32, 127) and char not in (3, 9, 10, 13):
            raise CCLRuntimeError(f"Instruction '<{self.name_parameter}': character with code {char} is not a printable ASCII character", traceback=self.traceback)

        # <Enter> keypress returns code 13 (\r, carriage return) which is supposed to be code 10 (\n, line feed)
        # And sometimes it returns code 3 (\EOT, end of text)...
        char = 10 if char in (3, 13) else char
        self.namespace.stdout += chr(char)


@dataclass
class StdIn(Instruction):
    name_parameter: str

    def callback(self):
        if self.name_parameter is None:
            raise CCLRuntimeError(f"Instruction '>_': name must be provided and cannot be '_'", traceback=self.traceback)

        cell_local = self.get_local_variable(self.name_parameter)
        cell_global = self.get_global_variable(self.name_parameter)

        if not cell_global and not cell_local:
            raise CCLRuntimeError(f"Instruction '>{self.name_parameter}': variable '{self.name_parameter}' is undefined", traceback=self.traceback)

        print()
        while True:
            char = getchar()
            if char in KeyIgnore:
                continue
            if len(char) > 1:
                raise CCLRuntimeError(f"Instruction '>{self.name_parameter}': bad input provided; input must be a printable ASCII character", traceback=self.traceback)
            if ord(char) not in range(32, 127) and ord(char) not in (3, 9, 10, 13):
                raise CCLRuntimeError(f"Instruction '>{self.name_parameter}': bad input provided; input must be a printable ASCII character", traceback=self.traceback)
            break

        if ord(char) in (3, 10, 13):
            char = '\n'
        self.namespace.stdout += char
        if cell_local:
            self.namespace.local_variables[self.name_parameter] = Cell(ord(char))
            return
        self.namespace.global_variables[self.name_parameter] = Cell(ord(char))


@dataclass
class StartCompare(Instruction):
    name_parameter: str
    jump_address: int

    def callback(self):
        if self.name_parameter is None:
            raise CCLRuntimeError(f"Instruction '?_': name must be provided and cannot be '_'", traceback=self.traceback)

        if not self.namespace.stack:
            raise CCLRuntimeError("Instruction '?': cannot compare with an empty stack", traceback=self.traceback)

        cell = self.get_local_variable(self.name_parameter)
        if not cell:
            cell = self.get_global_variable(self.name_parameter)
        if not cell:
            raise CCLRuntimeError(f"Instruction '?{self.name_parameter}': variable '{self.name_parameter}' is undefined", traceback=self.traceback)
        variable = cell._value

        if variable != self.namespace.stack[-1]:
            self.namespace.instruction_pointer = self.jump_address


@dataclass
class StartRepeat(Instruction):
    name_parameter: str
    jump_address: int
    uid: int

    def callback(self):
        cell = self.get_local_variable(self.name_parameter)
        if not cell:
            cell = self.get_global_variable(self.name_parameter)
        if not cell:
            raise CCLRuntimeError(f"Instruction '{self.name_parameter}[...]': variable '{self.name_parameter}' is undefined", traceback=self.traceback)
        amount = cell._value

        if amount < 0:
            raise CCLRuntimeError(f"Instruction '{self.name_parameter}[...]': parameter ('{self.name_parameter}' = {amount}) cannot be less than 0", traceback=self.traceback)

        if amount == 0:
            self.namespace.instruction_pointer = self.jump_address
            return

        self.namespace.global_variables[f'__repeat{self.uid}__'] = Cell(amount)
        self.namespace.instruction_pointer = self.jump_address - 1


@dataclass
class EndRepeat(Instruction):
    jump_address: int
    uid: int

    def callback(self):
        counter = self.namespace.global_variables[f'__repeat{self.uid}__']
        if counter == 0:
            self.namespace.global_variables.pop(f'__repeat{self.uid}__')
            return

        counter -= 1
        self.namespace.instruction_pointer = self.jump_address


@dataclass
class StartWhile(Instruction):
    def callback(self):
        pass


@dataclass
class EndWhile(Instruction):
    jump_address: int

    def callback(self):
        self.namespace.instruction_pointer = self.jump_address


@dataclass
class ExitBlock(Instruction):
    context: Context
    jump_address: int
    uid: int

    def callback(self):
        if self.context == Context.PROCEDURE:
            raise CCLExit

        if self.context == Context.REPEAT:
            self.namespace.global_variables.pop(f'__repeat{self.uid}__')

        self.namespace.instruction_pointer = self.jump_address


@dataclass
class ContinueBlock(Instruction):
    context: Context
    jump_address: int

    def callback(self):
        if self.context == Context.WHILE:
            self.namespace.instruction_pointer = self.jump_address
            return

        if self.context == Context.REPEAT:
            self.namespace.instruction_pointer = self.jump_address - 1
            return

        raise CCLRuntimeError(f"Instruction ':': cannot be used outside of REPEAT or WHILE block", traceback=self.traceback)


@dataclass
class EndCompare(Instruction):
    def callback(self):
        pass


@dataclass
class EndProcedure(Instruction):
    def callback(self):
        raise CCLExit
