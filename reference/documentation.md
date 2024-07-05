# Overview
This documentation is a general overview of CCL (cool char lang) language.
This section should give a general idea on what the language is, with the following
sections explaining individual instructions.

## The stack
CCL is stack-based.
Unlike in brainf, where you have more precise control over which "cells" you're modifying,
in CCL you are limited to stack operations.
New "cells" appear on top of the stack, while older "cells" are on bottom.

Another difference is the maximum and minimum value of each "cell".
In brainf, each cell holds an unsigned 1 byte integer [0, 255].
In CCL, each cell holds a **signed 2 byte integer** [-32768, +32767].

Just like in brainf, overflowing is allowed,
and it will simply result in the jump to the lowest negative / highest positive value.

The stack does not have a size limit, and can store as much cells as you'd like.
The only limit is the computer's RAM.

## Variables
CCL has variables. Variables are read-only,
so they can hold same range of values, as "cells" on the stack.

Everything in CCL is 1 character long, including variable names.

All variables are **global**, meaning they can be accessed in any procedure.
Variables, created inside of procedures, are always global, too.
Though, procedures also allow local variables, but on that later.

## Procedures
CCL also has procedures, which allow the reuse of the same code.
Unlike functions, procedures don't have a return value, and don't take any arguments.

However, you are able to "pass" arguments through the stack or the global variables.

Procedure names are also limited to 1 character.
Important note: variable and procedure names **are stored differently**!
It means that it is possible to have a variable and a procedure with the same name.

Procedures are defined at runtime. Also, it's possible to overwrite an already existing procedure.

## Instructions
Each instruction is **exactly 1 symbol long**, with some taking a **parameter as the second symbol**.
A few examples are: `^`, `$v`, `v {`.

In all cases parameter is a "name symbol", meaning it refers to a variable or a procedure.
Only english letters [a-z A-Z] are allowed as a "name symbol".
Sometimes, it's possible to use `_` instead of a name, which has a certain effect.

## Comments, newlines and spaces
CCL only has an inline comment, which starts with `/`, and **ends on a newline**.

Newlines, tabs and spaces **are not important** and are simply ignored.
It is possible to write code without using a single space or a newline.

Important note: **code will not run if it contains any "illegal symbols"**.
All symbols, that are not whitespace, not "name symbols" and not instructions
are considered "illegal". Though, they are ignored in comments.

# Stack
This section covers instructions that affect the stack in one way or another.

## PushZero: `^`
Takes no parameters.
Pushes a **new cell to the top of the stack**. Initial value of that cell is 0.

Note, that stack starts out empty,
so in many cases you have to push an empty element before other instructions.

### Usage example
Code:
```
^^^
```
Result:
```
-- STACK --
[ 0 ] <- top
[ 0 ]
[ 0 ]
```

## Increment: `+`
Takes no parameters.
Adds 1 **to the top cell on a stack**.

If stack is currently empty, will result in an error.

### Usage example
Code:
```
^+++
```
Result:
```
-- STACK --
[ 3 ] <- top
```

## Decrement: `-`
Takes no parameters.
Subtracts 1 **from the top cell on a stack**.

If stack is currently empty, will result in an error.

### Usage example
Code:
```
^----
```
Result:
```
-- STACK --
[ -4 ] <- top
```

## Add: `*`
Takes no parameters.
This instruction does two things at once:
1. Pops (deletes) top cell of a stack;
2. **Adds** popped cell's value to the next cell.

There needs to be at least 2 elements on a stack to execute this instruction.
Results in an error otherwise.

### Usage example
Code:
```
^++   // Pushes 2
^+++  // Pushes 3
*     // Adds top to the next
```
Result:
```
-- STACK --
[ 5 ] <- top
```

## Subtract: `~`
Takes no parameters.
This instruction does two things at once:
1. Pops (deletes) top cell of a stack;
2. **Subtracts** popped cell's value from the next cell.

There needs to be at least 2 elements on a stack to execute this instruction.
Results in an error otherwise.

### Usage example
Code:
```
^+++    // Pushes 3
^+++++  // Pushes 5
~       // Subtracts top from the next
```
Result:
```
-- STACK --
[ -2 ] <- top
```

## Reverse: `%v`
Takes a parameter (on the right). Parameter is a variable name or `_`.

If parameter is a variable name, it reverses the variable's value cells on the stack.
If parameter is `_`, reverses the entire stack.

Variable with a given name must exist.
Variable's value must not be less than 1, and must not exceed the amount of elements on the stack.

### Usage example
Code:
```
^+     // Pushes 1 (bottom)
^++    // Pushes 2 (middle)
^+++   // Pushes 3 (middle)
^++++  // Pushes 4 (top)
%_     // Reverses the whole stack
```
Result:
```
-- STACK --
[ 1 ] <- top
[ 2 ]
[ 3 ]
[ 4 ]
```


# Variables
This section covers instructions that affect variables in one way or another.

## Assign: `=v`
Takes a parameter (on the right). Parameter is a variable name or `_`.

Top cell on the stack is popped (deleted).

If parameter is a variable name, creates (or overrides) variable with a provided name.
Sets the value to the popped cell's value.

If parameter is `_`, does not create any variable, simply popping the top cell.

If stack is currently empty, will result in an error.

### Usage example
Code:
```
^+++ = v
```
Result:
```
-- STACK --
<empty>

-- VARIABLES --
GLOBAL v = 3
```

## Delete: `!v`
Takes a parameter (on the right). Parameter is a variable name, `_` is not allowed.

Deletes the provided variable. Referring to that variable after will result in an error.

If there is both local and global variable with a provided name, deletes **the local variable**.
Referring to that variable after will refer to the **global variable**.

Variable with a given name must exist.

### Usage example
Code:
```
^+++ = v  // global v = 3
!v        // delete v
```
Result:
```
-- STACK --
<empty>

-- VARIABLES --
<empty>
```

## Push: `$v`
Takes a parameter (on the right). Parameter is a variable name, `_` is not allowed.

Pushes **a new cell on top of the stack**,
and sets its initial value to the provided variable's value.

Variable with a given name must exist.

### Usage example
Code:
```
^+++ = v  // global v = 3
$v $v $v  // push v's value 3 times.
```
Result:
```
-- STACK --
[ 3 ] <- top
[ 3 ]
[ 3 ]

-- VARIABLES --
GLOBAL v = 3
```

## AssignLocal: `&v`
Takes a parameter (on the right). Parameter is a variable name, `_` is not allowed.

Can only be used inside of procedure block.

**Does not pop any cells from the stack**.
It creates a local variable with provided name and initial value of 0.
Referring to that variable after will refer to this local variable.

If local variable with such name already exists, **its value will be reset to 0**.

Local variables are stored separately from the global variables,
so it is possible for global and local variables to have same name.

Also, local variables are unique for each procedure,
so several procedures can use unique local variables with same name.

All local variables get deleted after procedure ends.

### Usage example
Code:
```
A {        // procedure A:
    &a     // local a
    ^ = a  // a = 0
}

^++ = a    // a = 2
@A         // call procedure A
```
Result:
```
-- STACK --
<empty>

-- VARIABLES --
GLOBAL a = 2

-- PROCEDURES --
A{...}
```

# Input and output
This section covers instructions that receive input and provide output.
These two instructions work almost same way as their alternatives in brainf.

## Output: `<v`
Takes a parameter (on the right). Parameter is a variable name, `_` is not allowed.

Outputs a single character to the console.
Interprets the variable's value as an ASCII code (for reference, look up `ascii.txt`).

Variable with a given name must exist.
Variable's value must be a printable ASCII character.

### Usage example
Code:
```
^++++++++++ = v  // v = 10
^ v[$v*]         // repeat v times: push v and add
= v              // v = 100 (ascii code for "d")
<v               // print v
```
Result:
```
-- OUTPUT --
d

-- STACK --
<empty>

-- VARIABLES --
GLOBAL v = 100
```

## Input: `>v`
Takes a parameter (on the right). Parameter is a variable name, `_` is not allowed.

Reads one character from the console.
Character's ASCII code (for reference, look up `ascii.txt`) is stored in a provided variable.

Variable with a given name must exist.
User input must be a printable ASCII character.

### Usage example
Code:
```
^ = v  // v = 0
>v     // input v (let's assume user pressed "d" with ASCII code 100)
```
Result:
```
-- OUTPUT --
d

-- STACK --
<empty>

-- VARIABLES --
GLOBAL v = 100
```


# Control flow (blocks)
This section covers the last and most important part of the language: control flow.

## Procedure block: `P{ ... }`
Takes a parameter (on the left). Parameter is a procedure name, `_` is not allowed.

Upon reaching `{`, defines a procedure with a provided name.
if such procedure already exists, overrides it.

Note that it is possible to define a procedure inside of a procedure.
It's also possible for procedure to redefine itself.

Code inside of procedure body (between `P{` and `}`) does not run, until the procedure is called.

### Usage example
Code:
```
P {         // procedure P:
    ^+++++  // push 5
}
```
Result:
```
-- STACK --
<empty>

-- VARIABLES --
<empty>

-- PROCEDURES --
P{...}
```

## Call: `@P`
Takes a parameter (on the right). Parameter is a variable name, `_` is not allowed.

Calls a procedure with a provided name.
After all the code inside of procedure is executed, program continues from this instruction.

It is possible to call procedure within itself. Language does support recursion.

Procedure with a given name must exist.

### Usage example
Code:
```
P {         // procedure P:
    ^+++++  // push 5
}

@P          // call P
```
Result:
```
-- STACK --
[ 5 ] <- top

-- VARIABLES --
<empty>

-- PROCEDURES --
P{...}
```

## Infinite block: `( ... )`
Upon reaching `)`, goes back to the corresponding `(`.

The only way to end the infinite loop is to use the break instruction (`#`).

### Usage example
Code:
```
^ = c   // c = 0

(       // while true:
    >c  // input c (infinitely reads characters)
)
```
Result:
```
-- OUTPUT --
dddddddd

-- STACK --
<empty>

-- VARIABLES --
GLOBAL c = 100
```

## Repeat block: `v[ ... ]`
Takes a parameter (on the left). Parameter is a variable name, `_` is not allowed.

Upon reaching `]`, goes back to the corresponding `v[`.

This block repeats itself provided variable's value times.

Changing variable's value inside of the block **does not affect how many times loop will happen**.
Repeat block remembers the initial value.

Variable with a given name must exist.
Variable's value cannot be less than 0.

### Usage example
Code:
```
^+++++ = v  // v = 5

v[          // for _ in range(v):
    ^+      // push 1
]
```
Result:
```
-- STACK --
[ 1 ]
[ 1 ]
[ 1 ]
[ 1 ]
[ 1 ]

-- VARIABLES --
GLOBAL v = 5
```

## End: `#`
This instruction is heavily context-dependant, and is able to perform 3 different things.
1. Inside of a loop (repeat block or infinite block), acts as a `break`, ending the loop;
2. Inside of a procedure, acts as `return`, and ends the procedure;
3. Outside of a procedure and outside of a loop, ends the program.

### Usage example
Code:
```
#       // program exits here 
^+++++
```
Result:
```
-- STACK --
<empty>
```

## Continue: `:`
This instruction can only be used inside of a repeat or infinite block.

Acts as a `continue`, ends the current iteration, and goes back to the start of a loop.

### Usage example
Code:
```
^+++++ = v  // v = 5

v [         // for _ in range(v):
    ^+      // push 1
    :       // continue
    ^++     // push 2 (unreachable)
]
```
Result:
```
-- STACK --
[ 1 ]
[ 1 ]
[ 1 ]
[ 1 ]
[ 1 ]

-- VARIABLES --
GLOBAL v = 5
```

## Conditional block: `?v ... ;`
Takes a parameter (on the right). Parameter is a variable name, `_` is not allowed.

Upon reaching `?v`, compares given variable's value with value of the top cell on the stack.

If comparison is true (v == top), does nothing, and program continues normally.

If comparison is false (v != top), jumps to the corresponding `;`.

Variable with a given name must exist.
If stack is currently empty, will result in an error.

### Usage example
Code:
```
^+ = v      // v = 1
^           // push 0

?v          // if top == v:
    ^+++++  // push 5 (skipped, due to condition being false)
;
```
Result:
```
-- STACK --
[ 0 ]

-- VARIABLES --
GLOBAL v = 1
```