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

### if

```
if (<expression>) {
    <statement>*
}
```

Executes the block if `<expression>` is truthy. The condition is currently
restricted to an equality comparison (`==`) or a bare value; there is no
`else`/`else if` yet, and blocks can be empty or nested.

```
var bob: str = "Hi";
if (bob == "Hi") {
    print("bob says hi");
}
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

There is no arithmetic, no string concatenation, and no other comparison
operators (`!=`, `<`, `>`, ...) yet. Equality comparison does not
type-check its operands — comparing an `int` to a `str` is allowed and
simply evaluates to `false` at runtime rather than being a parse error.

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
statement   := printStmt | varDecl | assignment | ifStmt
printStmt   := "print" "(" expression ")" ";"
varDecl     := "var" IDENTIFIER ":" type ("=" expression)? ";"
assignment  := IDENTIFIER "=" expression ";"
ifStmt      := "if" "(" expression ")" "{" statement* "}"
type        := "int" | "str"
expression  := primary ("==" primary)?
primary     := STRING | INT | IDENTIFIER | inputCall
inputCall   := "input" "(" STRING ")"
```

## Not yet implemented

- Arithmetic operators
- `else` / `else if`
- Comparison operators other than `==` (`!=`, `<`, `>`, ...)
- Boolean operators (`&&`, `||`, `!`)
- `while` / `for` loops
- Functions
- Comments
- Parsing `int` values typed via `input(...)` (input is always `str`)
