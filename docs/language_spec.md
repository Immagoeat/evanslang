# evanslang language spec

Source files use the `.el` extension.

## Statements

### print

```
print(<expression>);
```

Prints the value of `<expression>` followed by a newline.

```
print("Hello, World!");
print(EXAMPLE);
```

### var

```
var <NAME>: <type> = <expression>;
var <NAME>: <type>;
```

Declares a variable named `<NAME>` with the given `<type>`. The type
annotation is mandatory. If an initial `<expression>` is given, its type
must match the declared type — a mismatch is a compile-time (parse) error.
The second form declares the variable without a value; it must be assigned
before it's read (via `print` or used in another expression).

```
var EXAMPLE: str = "Hello";
var COUNT: int = 9;
var NAME: str;
```

### assignment

```
<NAME> = <expression>;
```

Assigns `<expression>` to a previously-declared variable `<NAME>`. The
variable must already exist (declared with `var`), and the value's type must
match the variable's declared type — both are compile-time (parse) errors
otherwise.

```
var bob: str;
bob = "Hi";
```

### compound assignment

```
<NAME> += <expression>;
<NAME> -= <expression>;
<NAME> *= <expression>;
<NAME> /= <expression>;
```

Shorthand for `<NAME> = <NAME> <op> <expression>;`. Only valid on `int`
variables; `<expression>` must be an integer literal or another `int`
variable (both are compile-time (parse) errors otherwise). Division uses
integer (floor) division; dividing by zero is a runtime error.

```
var bob: int = 10;
bob += 3;
print(bob);  # 13
bob -= 3;
print(bob);  # 10
bob *= 3;
print(bob);  # 30
bob /= 3;
print(bob);  # 10
```

### if / elseif / else

```
if (<expression>) {
    <statement>*
}
elseif (<expression>) {
    <statement>*
}
else {
    <statement>*
}
```

Executes the first block whose condition is truthy, falling through to
`else` if none match. `elseif` may repeat any number of times; `elseif` and
`else` are both optional. The condition is currently restricted to an
equality comparison (`==`) or a bare value. Blocks can be empty or nested.
A single optional `;` is allowed immediately after any block's closing
`}` (including after `if`/`elseif`, not only the last block) — it's purely
cosmetic and has no effect either way.

```
var bob: str = "Hi";
if (bob == "Hi") {
    print("bob says hi");
}
elseif (bob == "Hello") {
    print("bob says hello");
}
else {
    print("bob says something else");
}
```

### comments

```
# <anything to end of line>
```

Everything from `#` to the end of the line is ignored. Comments can appear
on their own line or after code on the same line, and don't need a
terminating character — the line break (or end of file) ends them.

```
# This program greets the user.
var bob: str = "Hi"; # inline comment
print(bob);
```

## Types

| Type  | Description               | Literal example |
|-------|----------------------------|------------------|
| `str` | Text, double-quoted        | `"Hello"`        |
| `int` | Whole numbers (no sign yet)| `9`               |

## Expressions

Currently supported expressions:
- String literals: `"..."`
- Integer literals: `9`
- Identifiers (referencing a previously declared `var`)
- `input("<prompt>")` — see below
- Equality comparisons: `<expr> == <expr>` (used in `if` conditions)
- Arithmetic (`+`, `-`, `*`, `/`) — currently only reachable through
  compound assignment (`+=`, `-=`, `*=`, `/=`), not as a general infix
  expression inside `print(...)` or elsewhere

There is no string concatenation and no comparison operators other than
`==` (`!=`, `<`, `>`, ...) yet. Equality comparison does not type-check its
operands — comparing an `int` to a `str` is allowed and simply evaluates to
`false` at runtime rather than being a parse error.

### input

```
input("<prompt>")
```

Prints `<prompt>` (no trailing newline) and reads a line of text from
stdin, returning it as a `str`. Only usable where a `str` value is expected
(assigning to or initializing an `int` variable with `input(...)` is a
parse error).

```
var bob: str;
bob = input("MESSAGE");
print(bob);
```

## Grammar (informal)

```
program        := statement*
statement      := printStmt | varDecl | assignment | compoundAssign | ifStmt
printStmt      := "print" "(" expression ")" ";"
varDecl        := "var" IDENTIFIER ":" type ("=" expression)? ";"
assignment     := IDENTIFIER "=" expression ";"
compoundAssign := IDENTIFIER ("+=" | "-=" | "*=" | "/=") (INT | IDENTIFIER) ";"
ifStmt         := "if" "(" expression ")" block ";"?
                  ("elseif" "(" expression ")" block ";"?)*
                  ("else" block ";"?)?
block          := "{" statement* "}"
type           := "int" | "str"
expression     := primary ("==" primary)?
primary        := STRING | INT | IDENTIFIER | inputCall
inputCall      := "input" "(" STRING ")"
```

## Not yet implemented

- Arithmetic as a general infix expression (only reachable via compound assignment right now)
- Comparison operators other than `==` (`!=`, `<`, `>`, ...)
- Boolean operators (`&&`, `||`, `!`)
- `while` / `for` loops
- Functions
- Block comments (`#` only comments to end of line)
- Parsing `int` values typed via `input(...)` (input is always `str`)
