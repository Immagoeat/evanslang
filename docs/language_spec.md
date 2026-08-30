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

There is no arithmetic and no string concatenation yet.

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
program     := statement*
statement   := printStmt | varDecl | assignment
printStmt   := "print" "(" expression ")" ";"
varDecl     := "var" IDENTIFIER ":" type ("=" expression)? ";"
assignment  := IDENTIFIER "=" expression ";"
type        := "int" | "str"
expression  := STRING | INT | IDENTIFIER | inputCall
inputCall   := "input" "(" STRING ")"
```

## Not yet implemented

- Arithmetic and boolean operators
- Control flow (`if`, `while`, `for`)
- Functions
- Comments
- Parsing `int` values typed via `input(...)` (input is always `str`)
