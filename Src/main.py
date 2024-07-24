from virtual_machine import *

vm = VirtualMachine()
main = Procedure(virtual_machine=vm)
main.instruction_stack = [
    PushZero(main, None),
    Increment(main, None), Increment(main, None), Increment(main, None),
    PushZero(main, None),
    Increment(main, None), Increment(main, None),
    Subtract(main, None)
]
vm.call_stack.append(main)

while vm.call_stack:
    vm.execute_next()

print(vm.stack)
