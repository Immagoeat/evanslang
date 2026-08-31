# evanslang language spec

Source files use the `.el` extension.

## Program structure

```
class main() {
    <statement>*
}
```

Every program's entire body must be inside `class main() { ... }` — it is
the mandatory entry point, similar to `main` in Java or C#. There is
nothing else at the top level: no statements before/after/outside the
block, and no other classes. A single optional `;` is allowed right after
the closing `}` (`class main() {...};`), purely cosmetic. `class main()`
is not itself a general-purpose class construct yet — it has no fields, no
methods beyond its body, and can't be instantiated; it exists solely to
mark where the program starts.

```
class main() {
    print("Hello, World!");
}
```

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
and `float` variables; `<expression>` must be a literal or variable of that
*same* type — `int` and `float` never mix, even between two variables
(both are compile-time (parse) errors otherwise). `/=` on `int` uses
integer (floor) division; on `float` it uses real division. Dividing by
zero is a runtime error either way.

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
`else` are both optional. The condition can be any expression, including
comparisons and boolean combinations (see Expressions below). Blocks can be
empty or nested. A single optional `;` is allowed immediately after any
block's closing `}` (including after `if`/`elseif`, not only the last
block) — it's purely cosmetic and has no effect either way.

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

| Type    | Description                            | Literal example |
|---------|------------------------------------------|------------------|
| `str`   | Text, double-quoted                     | `"Hello"`        |
| `int`   | Whole numbers (no sign yet)             | `9`              |
| `float` | Decimal numbers (requires a digit on both sides of the `.`) | `3.14` |
| `bool`  | `true` or `false`                       | `true`           |

`int` and `float` are always distinct — an `int` variable can never hold a
`float` value or vice versa, in `var`, plain assignment, or compound
assignment. There's no automatic widening (e.g. `int` → `float`).

## Expressions

Currently supported expressions:
- String literals: `"..."`
- Integer literals: `9`
- Float literals: `3.14` (a digit is required on both sides of the `.`)
- Boolean literals: `true`, `false`
- Identifiers (referencing a previously declared `var`)
- `input("<prompt>")` — see below
- Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Boolean operators: `&&` (and), `||` (or), `!` (not, prefix/unary)
- Arithmetic (`+`, `-`, `*`, `/`) — currently only reachable through
  compound assignment (`+=`, `-=`, `*=`, `/=`), not as a general infix
  expression inside `print(...)` or elsewhere

Precedence, loosest to tightest: `||`, then `&&`, then `!`, then the
comparison operators, then primaries (literals/identifiers/`input`). There
is no operator grouping with parentheses yet — `!` applies to the entire
comparison that follows it (`!a == b` means `!(a == b)`, not `(!a) == b`).

`==`/`!=` never type-check their operands — comparing an `int` to a `str`
is allowed and simply evaluates to `false`/`true` at runtime. `<`, `<=`,
`>`, `>=` do check at runtime: comparing values of different types (e.g.
an `int` to a `str`) raises a runtime error, matching Python's own
comparison semantics. `&&` and `||` do **not** short-circuit — both sides
are always evaluated, even if the left side alone determines the result
(this matters if a side has a visible effect, like `input(...)`).

`print(<bool>)` outputs `true`/`false` (lowercase, matching the literal
syntax), not Python-style `True`/`False`.

There is no string concatenation yet.

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

### .parse

```
<NAME>.parse
```

Converts a `str` variable's current value to a number, auto-detecting
`int` vs. `float` from the text at runtime (`"42"` → `int`, `"3.14"` →
`float`). `<NAME>` must be a previously-declared `str` variable — calling
`.parse` on a non-`str` or undeclared variable is a parse-time error. Since
the resulting type depends on the string's *contents* (not knowable until
the program runs), `bob.parse` is accepted as the initializer/assigned
value for both `int` and `float` variables at parse time; if the runtime
type doesn't actually match what gets stored, that mismatch isn't caught.
If the string isn't a valid number at all, `.parse` raises a runtime
error. `.parse` can be used as an expression (assigned or passed to
`print`) or as a bare statement (`bob.parse;`), in which case the result
is simply discarded.

```
var bob: str = "42";
var n: int = bob.parse;
print(n);

var pi_str: str = "3.14";
var pi: float = pi_str.parse;
print(pi);
```

## Grammar (informal)

```
program        := "class" "main" "(" ")" block ";"?
statement      := printStmt | varDecl | assignment | compoundAssign | ifStmt | exprStmt
printStmt      := "print" "(" expression ")" ";"
varDecl        := "var" IDENTIFIER ":" type ("=" expression)? ";"
assignment     := IDENTIFIER "=" expression ";"
compoundAssign := IDENTIFIER ("+=" | "-=" | "*=" | "/=") (INT | FLOAT | IDENTIFIER) ";"
ifStmt         := "if" "(" expression ")" block ";"?
                  ("elseif" "(" expression ")" block ";"?)*
                  ("else" block ";"?)?
exprStmt       := expression ";"    # currently only reachable via IDENTIFIER "." "parse"
block          := "{" statement* "}"
type           := "int" | "str" | "float" | "bool"
expression     := or
or             := and ("||" and)*
and            := not ("&&" not)*
not            := "!" not | comparison
comparison     := primary (("==" | "!=" | "<" | "<=" | ">" | ">=") primary)?
primary        := STRING | INT | FLOAT | "true" | "false" | IDENTIFIER ("." "parse")? | inputCall
inputCall      := "input" "(" STRING ")"
```

## Not yet implemented

- Arithmetic as a general infix expression (only reachable via compound assignment right now)
- Operator grouping with parentheses (e.g. `(a || b) && c`)
- Short-circuit evaluation of `&&`/`||`
- `while` / `for` loops
- Functions
- Block comments (`#` only comments to end of line)
- `.parse`-equivalent for `bool` (a `str` can't currently be converted to `bool`)
- Real classes: fields, methods, instantiation (`new`), multiple classes, inheritance — `class main()` currently only marks the program's entry point
