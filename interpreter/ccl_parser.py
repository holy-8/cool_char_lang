import string
from typing import Generator
from dataclasses import dataclass
from enum import StrEnum
from ccl_exceptions import CCLParseError, CCLTraceback
from ccl_internals import Context
from ccl_internals import (MainProcedure, Instruction,
                           DefineProcedure, CallProcedure, EndProcedure,
                           Add, Subtract, PopAdd, PopSubtract, Reverse,
                           PushZero, Assign, CreateLocal, Delete, PushVariable,
                           StdOut, StdIn,
                           StartCompare, EndCompare,
                           StartRepeat, EndRepeat, StartWhile, EndWhile,
                           ExitBlock, ContinueBlock)

@dataclass
class ParseContext:
    """IMPORTANT: start_address and end_address are instruction indexes within instruction_stack"""
    start_address: int
    end_address: int
    symbol: str
    symbol_end: str


@dataclass
class ContextProcedure(ParseContext):
    """IMPORTANT: start_address and end_address are positions in the source code"""
    start_address: tuple[int, int]
    end_address: tuple[int, int]
    symbol: str = '{'
    symbol_end: str = '}'


@dataclass
class ContextRepeat(ParseContext):
    """IMPORTANT: start_address and end_address are instruction indexes within instruction_stack"""
    uid: int = -1
    symbol: str = '['
    symbol_end: str = ']'


@dataclass
class ContextWhile(ParseContext):
    """IMPORTANT: start_address and end_address are instruction indexes within instruction_stack"""
    symbol: str = '('
    symbol_end: str = ')'


@dataclass
class ContextCompare(ParseContext):
    """IMPORTANT: start_address and end_address are instruction indexes within instruction_stack"""
    symbol: str = '?'
    symbol_end: str = ';'
    position_end: int = -1
    name_parameter: str = ''

@dataclass
class ContextComment(ParseContext):
    """IMPORTANT: start_address and end_address are unused by this Context"""
    start_address: int = -1
    end_address: int = -1
    symbol: str = '/'
    symbol_end: str = '\n'


class Symbols(StrEnum):
    NAME = string.ascii_letters
    NAME_BLANK = string.ascii_letters + '_'
    INSTRUCTION_SIMPLE = '^+-*~'
    INSTRUCTION_PARAMETER = '@=!&$%<>'
    REQUIRE_NAME_BEFORE = '{['
    REQUIRE_NAME_AFTER = '@=!&$%<>?'
    ALL = string.ascii_letters + '_' + '{}[]()?;' + '@=!&$%<>^+-*~#:/'
    SKIPPABLE = ' \t'


class Parser:
    def __init__(self, source_filepath: str) -> None:
        with open(source_filepath, encoding='utf-8') as source:
            self.code = source.read().splitlines()

        self.main = MainProcedure()
        self.parse_context: list[ParseContext] = list()
        self.compare_blocks: list[str] = list()
        self.skip_to_position: list[tuple[int, int]] = list()
        self.prev_symbol = ' '
        self.instruction_uid = 0

    def check_empty_code(self) -> bool:
        """Returns True if code is completely empty or does only contain whitespace"""
        if not self.code:
            return True
        for line in self.code:
            if line.strip():
                return False
        else:
            return True

    def iterate_code(self, from_line: int = 1, from_symbol: int = 0) -> Generator | tuple:
        """
        Yields (symbol, traceback) tuple, starting from line 'from_line', and symbol 'from_symbol'
        Returns an empty tuple if code is empty, so that a for loop can be skipped
        """
        if self.check_empty_code():
            return tuple()

        code_slice = self.code[from_line - 1:]
        code_slice[0] = code_slice[0][from_symbol:]
        line_index = from_line
        symbol_index = from_symbol

        for line in code_slice:
            for symbol in line:
                yield symbol, CCLTraceback(position=(line_index, symbol_index), line=line)
                symbol_index += 1
            line_index += 1
            symbol_index = 0
            if ContextComment() in self.parse_context:
                self.parse_context.remove(ContextComment())

    def check_skippable(self, symbol: str) -> bool:
        """Returns True if provided symbol has to be skipped"""
        if ContextComment() in self.parse_context:
            return True
        elif symbol in Symbols.SKIPPABLE:
            return True
        elif symbol == '/':
            self.parse_context.append(ContextComment())
            return True
        return False

    def check_unknown(self, symbol: str, traceback: CCLTraceback) -> None:
        """Raises CCLParseError if provided symbol is unknown"""
        if symbol not in Symbols.ALL:
            raise CCLParseError(f"Unknown symbol '{symbol}'", traceback=traceback)

    def check_parameter(self, symbol: str, traceback: CCLTraceback) -> None:
        """Raises CCLParseError if required parameter is not provided"""
        if symbol not in Symbols.REQUIRE_NAME_BEFORE and self.prev_symbol in Symbols.NAME:
            raise CCLParseError(f"Expected '[' or '{{' after name symbol '{self.prev_symbol}', got '{symbol}' instead", traceback=traceback)
        if symbol in Symbols.REQUIRE_NAME_BEFORE and self.prev_symbol not in Symbols.NAME:
            raise CCLParseError(f"Expected name symbol before '{symbol}', got '{self.prev_symbol}' instead", traceback=traceback)
        if self.prev_symbol in Symbols.REQUIRE_NAME_AFTER and symbol not in Symbols.NAME_BLANK:
            raise CCLParseError(f"Expected name symbol after '{self.prev_symbol}', got '{symbol}' instead", traceback=traceback)
        return None

    def parse_simple_instruction(self, symbol: str,
                                 namespace: MainProcedure | None,
                                 traceback: CCLTraceback) -> Instruction | None:
        """If symbol is a simple instruction, returns Instruction object, otherwise returns None"""
        if symbol not in Symbols.INSTRUCTION_SIMPLE:
            return None
        if symbol == '^':
            return PushZero(namespace=namespace, traceback=traceback)
        if symbol == '+':
            return Add(namespace=namespace, traceback=traceback)
        if symbol == '-':
            return Subtract(namespace=namespace, traceback=traceback)
        if symbol == '*':
            return PopAdd(namespace=namespace, traceback=traceback)
        if symbol == '~':
            return PopSubtract(namespace=namespace, traceback=traceback)

    def parse_parameter_instruction(self, symbol: str,
                                    namespace: MainProcedure | None,
                                    traceback: CCLTraceback) -> Instruction | None:
        """If symbol is a parameter instruction, returns Instruction object, otherwise returns None"""
        if self.prev_symbol not in Symbols.INSTRUCTION_PARAMETER:
            return None

        name = None if symbol == '_' else symbol

        if self.prev_symbol == '@':
            return CallProcedure(namespace=namespace, traceback=traceback, name_parameter=name)
        if self.prev_symbol == '=':
            return Assign(namespace=namespace, traceback=traceback, name_parameter=name)
        if self.prev_symbol == '!':
            return Delete(namespace=namespace, traceback=traceback, name_parameter=name)
        if self.prev_symbol == '&':
            return CreateLocal(namespace=namespace, traceback=traceback, name_parameter=name)
        if self.prev_symbol == '$':
            return PushVariable(namespace=namespace, traceback=traceback, name_parameter=name)
        if self.prev_symbol == '%':
            return Reverse(namespace=namespace, traceback=traceback, name_parameter=name)
        if self.prev_symbol == '<':
            return StdOut(namespace=namespace, traceback=traceback, name_parameter=name)
        if self.prev_symbol == '>':
            return StdIn(namespace=namespace, traceback=traceback, name_parameter=name)

    def lookahead_symbol(self, start_address: int,
                         end_context: ParseContext,
                         traceback: CCLTraceback) -> None:
        """
        'start_address' is required for '[]', '()' and '?;' blocks
        Lookahead for the closing context 'end_context'
        Raises CCLParseError if opening symbol is unmatched
        Will also raise an error if closing symbol was found without a corresponing opening symbol
        On success, appends ParseContext object to parse_context list and returns None.
        """
        from_line = traceback.position[0]
        from_symbol = traceback.position[1]
        initial_prev_symbol = self.prev_symbol
        initial_context_len = len(self.parse_context)

        cur_address = start_address
        for symbol, inner_traceback in self.iterate_code(from_line, from_symbol):
            if inner_traceback.position != traceback.position:
                if self.check_skippable(symbol):
                    continue
                self.check_unknown(symbol, inner_traceback)
                self.check_parameter(symbol, inner_traceback)
            if symbol == '{':
                self.parse_context.append(ContextProcedure(inner_traceback.position, -1))
            elif symbol == '}':
                if not isinstance(self.parse_context[-1], ContextProcedure):
                    raise CCLParseError(f"Unexpected '}}': expected '{self.parse_context[-1].symbol_end}' after '{self.parse_context[-1].symbol}'", traceback=inner_traceback)
                result_context = self.parse_context.pop()
                result_context.end_address = inner_traceback.position
            elif symbol == '[':
                self.instruction_uid += 1
                self.parse_context.append(ContextRepeat(cur_address, -1, uid=self.instruction_uid))
            elif symbol == ']':
                if not isinstance(self.parse_context[-1], ContextRepeat):
                    raise CCLParseError(f"Unexpected ']': expected '{self.parse_context[-1].symbol_end}' after '{self.parse_context[-1].symbol}'", traceback=inner_traceback)
                result_context = self.parse_context.pop()
                result_context.end_address = cur_address
            elif symbol == '(':
                self.parse_context.append(ContextWhile(cur_address, -1))
            elif symbol == ')':
                if not isinstance(self.parse_context[-1], ContextWhile):
                    raise CCLParseError(f"Unexpected ')': expected '{self.parse_context[-1].symbol_end}' after '{self.parse_context[-1].symbol}'", traceback=inner_traceback)
                result_context = self.parse_context.pop()
                result_context.end_address = cur_address
            elif symbol == '?':
                self.parse_context.append(ContextCompare(cur_address, -1))
            elif symbol == ';':
                if not isinstance(self.parse_context[-1], ContextCompare):
                    raise CCLParseError(f"Unexpected ';': expected '{self.parse_context[-1].symbol_end}' after '{self.parse_context[-1].symbol}'", traceback=inner_traceback)
                result_context = self.parse_context.pop()
                result_context.end_address = cur_address
            if len(self.parse_context) == initial_context_len:
                self.prev_symbol = initial_prev_symbol
                self.parse_context.append(result_context)
                return None
            if symbol not in Symbols.NAME_BLANK:
                cur_address += 1
            if symbol in Symbols.NAME_BLANK and self.prev_symbol in Symbols.REQUIRE_NAME_AFTER:
                self.prev_symbol = ' '
                if isinstance(self.parse_context[-1], ContextCompare):
                    if not self.parse_context[-1].name_parameter:
                        self.parse_context[-1].name_parameter = symbol
                        self.parse_context[-1].position_end = inner_traceback.position
            else:
                self.prev_symbol = symbol

        raise CCLParseError(f"'{end_context.symbol}' was never closed", traceback=traceback)

    def parse_define_procedure(self, symbol: str,
                               namespace: MainProcedure | None,
                               traceback: CCLTraceback) -> Instruction | None:
        """If symbol is a define procedure instruction, returns Instruction object, otherwise returns None"""
        if symbol != '{':
            return None

        name = self.prev_symbol
        self.prev_symbol = '{'
        from_line = traceback.position[0]
        from_symbol = traceback.position[1] + 1
        self.lookahead_symbol(-1, ContextProcedure, traceback)
        end_position = self.parse_context[-1].end_address

        instruction_stack = list()
        for symbol, inner_traceback in self.iterate_code(from_line, from_symbol):
            if self.skip_to_position:
                if inner_traceback.position == self.skip_to_position[-1]:
                    self.skip_to_position.pop()
                continue
            if inner_traceback.position == end_position:
                break
            if self.check_skippable(symbol):
                continue
            self.check_unknown(symbol, inner_traceback)
            self.check_parameter(symbol, inner_traceback)

            if instruction := self.parse_simple_instruction(symbol, None, inner_traceback):
                instruction_stack.append(instruction)
                self.prev_symbol = symbol
                continue

            if instruction := self.parse_parameter_instruction(symbol, None, inner_traceback):
                instruction_stack.append(instruction)
                self.prev_symbol = ' '
                continue

            if instruction := self.parse_define_procedure(symbol, None, inner_traceback):
                instruction_stack.append(instruction)
                continue

            if instruction := self.parse_repeat_block(len(instruction_stack), symbol, None, inner_traceback):
                instruction_stack.append(instruction)
                continue

            if instruction := self.parse_while_block(len(instruction_stack), symbol, None, inner_traceback):
                instruction_stack.append(instruction)
                continue

            if instruction := self.parse_compare_block(len(instruction_stack), symbol, None, inner_traceback):
                instruction_stack.append(instruction)
                continue

            if instruction := self.parse_exit_instruction(symbol, None, inner_traceback):
                instruction_stack.append(instruction)
                continue

            if instruction := self.parse_continue_instruction(symbol, None, inner_traceback):
                instruction_stack.append(instruction)
                continue

            if symbol == '}':
                raise CCLParseError("Unexpected '}'", traceback=traceback)

            self.prev_symbol = symbol

        instruction = DefineProcedure(namespace=namespace, traceback=traceback, name_parameter=name, instruction_stack=instruction_stack)
        self.prev_symbol = '}'
        self.skip_to_position.append(end_position)
        return instruction

    def parse_repeat_block(self, start_address: int,
                           symbol: str,
                           namespace: MainProcedure | None,
                           traceback: CCLTraceback) -> Instruction | None:
        """If symbol is a repeat block instruction, returns Instruction object, otherwise returns None"""
        if symbol not in '[]':
            return None

        if symbol == '[':
            name = self.prev_symbol
            self.prev_symbol = symbol
            self.lookahead_symbol(start_address, ContextRepeat, traceback)
            context = self.parse_context[-1]
            return StartRepeat(namespace=namespace, traceback=traceback, name_parameter=name,
                               jump_address=context.end_address, uid=context.uid)
        elif symbol == ']':
            self.prev_symbol = symbol
            if not self.parse_context:
                raise CCLParseError(f"Unexpected ']'", traceback=traceback)
            context = self.parse_context.pop()
            return EndRepeat(namespace=namespace, traceback=traceback,
                             jump_address=context.start_address, uid=context.uid)

    def parse_while_block(self, start_address: int,
                          symbol: str,
                          namespace: MainProcedure | None,
                          traceback: CCLTraceback) -> Instruction | None:
        """If symbol is a while block instruction, returns Instruction object, otherwise returns None"""
        if symbol not in '()':
            return None

        if symbol == '(':
            self.prev_symbol = symbol
            self.lookahead_symbol(start_address, ContextWhile, traceback)
            return StartWhile(namespace=namespace, traceback=traceback)
        elif symbol == ')':
            self.prev_symbol = symbol
            if not self.parse_context:
                raise CCLParseError(f"Unexpected ')'", traceback=traceback)
            context = self.parse_context.pop()
            return EndWhile(namespace=namespace, traceback=traceback, jump_address=context.start_address)

    def parse_compare_block(self, start_address: int,
                            symbol: str,
                            namespace: MainProcedure | None,
                            traceback: CCLTraceback) -> Instruction | None:
        """If symbol is a compare block instruction, returns Instruction object, otherwise returns None"""
        if symbol not in '?;':
            return None

        if symbol == '?':
            self.prev_symbol = ' '
            self.lookahead_symbol(start_address, ContextCompare, traceback)
            context = self.parse_context.pop()
            self.skip_to_position.append(context.position_end)
            self.compare_blocks.append('?')
            return StartCompare(namespace=namespace, traceback=traceback, name_parameter=context.name_parameter, jump_address=context.end_address)
        elif symbol == ';':
            self.prev_symbol = symbol
            if not self.compare_blocks:
                raise CCLParseError(f"Unexpected ';'", traceback=traceback)
            self.compare_blocks.pop()
            return EndCompare(namespace=namespace, traceback=traceback)

    def parse_exit_instruction(self, symbol: str,
                               namespace: MainProcedure | None,
                               traceback: CCLTraceback) -> Instruction | None:
        """If symbol is an exit instruction, returns Instruction object, otherwise returns None"""
        if symbol != '#':
            return None

        self.prev_symbol = '#'

        if not self.parse_context:
            return ExitBlock(namespace=namespace, traceback=traceback, context=Context.PROCEDURE, jump_address=None, uid=-1)

        if self.parse_context[-1].symbol == '{':
            return ExitBlock(namespace=namespace, traceback=traceback, context=Context.PROCEDURE, jump_address=None, uid=-1)

        if self.parse_context[-1].symbol == '[':
            return ExitBlock(namespace=namespace, traceback=traceback, context=Context.REPEAT,
                             jump_address=self.parse_context[-1].end_address, uid=self.parse_context[-1].uid)

        if self.parse_context[-1].symbol == '(':
            return ExitBlock(namespace=namespace, traceback=traceback, context=Context.WHILE,
                             jump_address=self.parse_context[-1].end_address, uid=-1)

    def parse_continue_instruction(self, symbol: str,
                               namespace: MainProcedure | None,
                               traceback: CCLTraceback) -> Instruction | None:
        """If symbol is an exit instruction, returns Instruction object, otherwise returns None"""
        if symbol != ':':
            return None

        self.prev_symbol = ':'

        if not self.parse_context:
            return ContinueBlock(namespace=namespace, traceback=traceback, context=Context.PROCEDURE, jump_address=-1)

        if self.parse_context[-1].symbol == '{':
            return ContinueBlock(namespace=namespace, traceback=traceback, context=Context.PROCEDURE, jump_address=-1)

        if self.parse_context[-1].symbol == '[':
            return ContinueBlock(namespace=namespace, traceback=traceback, context=Context.REPEAT,
                                 jump_address=self.parse_context[-1].end_address)

        if self.parse_context[-1].symbol == '(':
            return ContinueBlock(namespace=namespace, traceback=traceback, context=Context.WHILE,
                                 jump_address=self.parse_context[-1].start_address)

    def parse(self) -> MainProcedure:
        for symbol, traceback in self.iterate_code():
            if self.skip_to_position:
                if traceback.position == self.skip_to_position[-1]:
                    self.skip_to_position.pop()
                continue
            if self.check_skippable(symbol):
                continue
            self.check_unknown(symbol, traceback)
            self.check_parameter(symbol, traceback)

            if instruction := self.parse_simple_instruction(symbol, self.main, traceback):
                self.main.instruction_stack.append(instruction)
                self.prev_symbol = symbol
                continue

            if instruction := self.parse_parameter_instruction(symbol, self.main, traceback):
                self.main.instruction_stack.append(instruction)
                self.prev_symbol = ' '
                continue

            if instruction := self.parse_define_procedure(symbol, self.main, traceback):
                self.main.instruction_stack.append(instruction)
                continue

            if instruction := self.parse_repeat_block(len(self.main.instruction_stack), symbol, self.main, traceback):
                self.main.instruction_stack.append(instruction)
                continue

            if instruction := self.parse_while_block(len(self.main.instruction_stack), symbol, self.main, traceback):
                self.main.instruction_stack.append(instruction)
                continue

            if instruction := self.parse_compare_block(len(self.main.instruction_stack), symbol, self.main, traceback):
                self.main.instruction_stack.append(instruction)
                continue

            if instruction := self.parse_exit_instruction(symbol, self.main, traceback):
                self.main.instruction_stack.append(instruction)
                continue

            if instruction := self.parse_continue_instruction(symbol, self.main, traceback):
                self.main.instruction_stack.append(instruction)
                continue

            if symbol == '}':
                raise CCLParseError("Unexpected '}'", traceback=traceback)

            self.prev_symbol = symbol

        self.main.instruction_stack.append(
            EndProcedure(namespace=self.main, traceback=None)
        )
        return self.main
