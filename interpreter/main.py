import os, sys
from colorama import just_fix_windows_console, Fore, Back
from click import getchar
from ccl_parser import Parser
from ccl_exceptions import CCLExit, CCLParseError, CCLRuntimeError
from ccl_internals import DefineProcedure, EndProcedure

just_fix_windows_console()


def print_usage():
    print('USAGE: CCL! <filepath> [-args...]')
    print('ARGUMENTS:')
    print('    -showstack    Show entire instruction stack of the program and exit')
    print('    -ss           Alias for `-showstack`')
    print('    -debug        Interpret program in debug mode')
    print('    -d            Alias for `-debug`')
    print()


def check_argv(arglist: list[str]) -> Parser:
    if len(sys.argv) == 1:
        print_usage()
        print('ERROR: <filepath> was not provided')
        print()
        sys.exit(1)
    for arg in sys.argv[2:]:
        if arg not in arglist:
            print_usage()
            print(f"ERROR: unknown argument '{arg}'")
            print()
            sys.exit(1)
    try:
        return Parser(sys.argv[1])
    except FileNotFoundError:
        print_usage()
        print(f"ERROR: file '{sys.argv[1]}' was not found")
        print()
        sys.exit(1)
    except IsADirectoryError:
        print_usage()
        print(f"ERROR: path '{sys.argv[1]}' must lead to a file, but it leads to a directory")
        print()
        sys.exit(1)
    except PermissionError:
        print_usage()
        print(f"ERROR: cannot access path '{sys.argv[1]}': permission denied")
        print()
        sys.exit(1)


def try_show_stack(parser: Parser):
    if '-showstack' not in sys.argv and '-ss' not in sys.argv:
        return
    main = parser.parse()
    for instruction in main.instruction_stack:
        if isinstance(instruction, DefineProcedure):
            print(f"DefineProcedure(namespace={instruction.namespace}, traceback={instruction.traceback}, name_parameter='{instruction.name_parameter}')")
            for procedure_instruction in instruction.instruction_stack:
                print(f'    -> {instruction.name_parameter}::{procedure_instruction}')
                print()
        else:
            print(instruction)
        print()
    sys.exit(0)


def try_debug(parser: Parser):
    if '-debug' not in sys.argv and '-d' not in sys.argv:
        return
    try:
        main = parser.parse()
        main.debug_mode = True
        while True:
            os.system('cls')
            if not (isinstance(main.instruction_stack[main.instruction_pointer], EndProcedure)
                    and main.instruction_stack[main.instruction_pointer].traceback is None
                    and len(main.call_stack) == 0):
                if main.call_stack:
                    instruction = main.call_stack[-1].instruction_stack[main.call_stack[-1].instruction_pointer]
                    traceback = instruction.traceback
                    index = traceback.position[1]
                else:
                    instruction = main.instruction_stack[main.instruction_pointer]
                    traceback = instruction.traceback
                    index = traceback.position[1]
                print(f'[DEBUG]: at line {traceback.position[0]}, at symbol {traceback.position[1]}')
                print(f'[DEBUG]: in namespace {instruction.namespace}')
                formatted_line = (
                    traceback.line[:index]
                    + Back.LIGHTGREEN_EX + Fore.BLACK + traceback.line[index] + Back.RESET + Fore.RESET
                    + traceback.line[index + 1:]
                )
                if traceback.position[0] - 2 >= 0:
                    print(f'ln [ {traceback.position[0] - 1} ]: ' + parser.code[traceback.position[0] - 2])
                print(Fore.LIGHTGREEN_EX + f'ln [ {traceback.position[0]} ]:' + Fore.RESET + ' ' + formatted_line)
                try:
                    print(f'ln [ {traceback.position[0] + 1} ]: ' + parser.code[traceback.position[0]])
                except IndexError:
                    pass
                print()
                print(f"[DEBUG]: ID of instruction namespace: {id(instruction.namespace)}")
                print(f"[DEBUG]: ID of current instruction: {id(instruction)}")
                if isinstance(instruction, DefineProcedure):
                    print(f"[DEBUG]: DefineProcedure(namespace={instruction.namespace}, traceback=<...>, name_parameter='{instruction.name_parameter}', instruction_stack=<...>)")
                else:
                    print(f'[DEBUG]: {instruction}')
                print()
            main.next_instruction()
            main.debug()
            print()
            print('[DEBUG]: press any key to continue...')
            getchar()
    except CCLExit:
        main.debug()
        print(Fore.LIGHTGREEN_EX + 'Process finished with exit code 0\n' + Fore.RESET)
        sys.exit(0)
    except (CCLParseError, CCLRuntimeError) as Error:
        main.debug()
        print(f'Error occurred at line {Error.traceback.position[0]}:')
        err_index = Error.traceback.position[1]
        formatted_line = (
            Error.traceback.line[:err_index]
            + Back.LIGHTRED_EX + Fore.BLACK + Error.traceback.line[err_index] + Back.RESET + Fore.RESET
            + Error.traceback.line[err_index + 1:]
        )
        print(formatted_line)
        print(f'{Error.__class__.__name__}: {Error}\n')
        print(Fore.LIGHTRED_EX + 'Process finished with exit code 1\n' + Fore.RESET)
        sys.exit(1)


def run_normally(parser: Parser):
    try:
        main = parser.parse()
        while True:
            main.next_instruction()
            main.print_stdout()
    except CCLExit:
        print()
        main.debug()
        print(Fore.LIGHTGREEN_EX + 'Process finished with exit code 0\n' + Fore.RESET)
    except (CCLParseError, CCLRuntimeError) as Error:
        print(f'Error occurred at line {Error.traceback.position[0]}:')
        err_index = Error.traceback.position[1]
        formatted_line = (
            Error.traceback.line[:err_index]
            + Back.LIGHTRED_EX + Fore.BLACK + Error.traceback.line[err_index] + Back.RESET + Fore.RESET
            + Error.traceback.line[err_index + 1:]
        )
        print(formatted_line)
        print(f'{Error.__class__.__name__}: {Error}\n')
        print(Fore.LIGHTRED_EX + 'Process finished with exit code 1\n' + Fore.RESET)


def interpreter():
    arglist = ['-showstack', '-ss', '-debug', '-d']
    parser = check_argv(arglist)
    try_show_stack(parser)
    try_debug(parser)
    run_normally(parser)


if __name__ == '__main__':
    interpreter()
