# evanslang language spec

Source files use the `.el` extension.

## Program structure

A file is a sequence of `@mentions` imports (optional, must come first),
followed by any number of named classes:

```
@mentions <file> -> <alias>;
...

class <NAME>() { <statement>* }
class <NAME>(ment) { <statement>* }
```

A class is a named, callable block of statements — not a general-purpose
OOP class yet (see "Not yet implemented"). Two names are reserved with
special meaning; everything else is an ordinary, freely-named class:

- **`main`** — the program's entry point. A file being run directly
  (`evlng --build`/`--run`) must define `class main() { ... }`; its body
  runs first (after `init`, if present). A file that's only ever
  `@mentions`-ed by another file doesn't need one.
- **`init`** — optional. If present, its body runs once, automatically,
  before `main`, in the same file.
- **any other name** — not run automatically. Only executes when called,
  either locally (`NAME;`, from anywhere in the same file, including
  before its own declaration) or via `@mentions` (`alias.NAME;`, from
  another file — see below).

`main` and `init` behave this way regardless of `(ment)` — that modifier
has no effect on local behavior; it only controls cross-file visibility
(see `@mentions` below). A single optional `;` is allowed right after any
class's closing `}`, purely cosmetic.

```
class main() {
    print("Hello, World!");
}
```

### calling a class

```
<NAME>;
<ALIAS>.<NAME>;
```

Calling a class runs its body right there, like a named, parameterless
procedure — not object instantiation (there is no `new`, no fields, no
`this`). `NAME;` calls a class declared in the same file. `ALIAS.NAME;`
calls a class from a file brought in with `@mentions` (below). Calls can
appear anywhere a statement can, including inside other classes' bodies,
`if` blocks, etc., and one class can call another any number of times.
There is no return value and no parameters.

```
class helper() {
    print("helper running");
}

class main() {
    helper;
    helper;   # can be called more than once
}
```

### @mentions

```
@mentions <file> -> <alias>;
```

Imports another `.el` file (resolved relative to the file containing the
`@mentions` line) under `<alias>`, resolved and compiled together with
this file at build time (`evlng --build`). Only classes declared
`(ment)` in the mentioned file become reachable, as `<alias>.<NAME>;` —
classes without `(ment)` are invisible from outside their own file, even
though they're still callable locally within it. The mentioned file's own
`class main()` (if it even has one) is never run and has no special
meaning to the importer — only its `(ment)` classes matter.

`@mentions` only sees classes declared directly in the file it names —
importing a file does not transitively expose whatever *that* file itself
mentions. A cycle (file A mentions file B which mentions file A, directly
or through a longer chain) is a build-time error.

```
@mentions test.el -> test;

class main() {
    test.sdgdsg;
}
```

with `test.el` containing:

```
class sdgdsg(ment) {
    print("Hello from another file!");
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
program        := mention* classDecl+
mention        := "@" "mentions" filename "->" IDENTIFIER ";"
filename       := IDENTIFIER ("." IDENTIFIER)*
classDecl      := "class" IDENTIFIER "(" "ment"? ")" block ";"?
statement      := printStmt | varDecl | assignment | compoundAssign | ifStmt | exprStmt | callStmt
callStmt       := IDENTIFIER ";" | IDENTIFIER "." IDENTIFIER ";"
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

A file that defines no `class main()` still parses successfully as long
as it has at least one class or mention — it's only rejected (at build
time, not parse time) if it's the file actually being compiled/run.

## Not yet implemented

- Arithmetic as a general infix expression (only reachable via compound assignment right now)
- Operator grouping with parentheses (e.g. `(a || b) && c`)
- Short-circuit evaluation of `&&`/`||`
- `while` / `for` loops
- Functions
- Block comments (`#` only comments to end of line)
- `.parse`-equivalent for `bool` (a `str` can't currently be converted to `bool`)
- Real OOP: fields, methods (beyond a single callable body), `new`/instantiation, `this`, inheritance, parameters, return values — classes are currently just named, callable blocks of statements
- Quoted/path-style `@mentions` filenames (e.g. subdirectories) — the filename is a bare dotted identifier sequence, so it must look like a valid identifier chain (`utils.el`, not `"../lib/utils.el"`)
