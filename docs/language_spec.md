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
`if`/`while`/`for` bodies, etc., and one class can call another any number
of times, including recursively (bounded — see "call depth" below).
There is no return value and no parameters.

`NAME;` (the unaliased, local form) cannot target `main` or `init` in the
*same* file — both already run automatically, so calling either explicitly
would run its body a second time; this is rejected at parse time. This
restriction is specific to local calls: `alias.main;`/`alias.init;` are
fine, since a *mentioned* file's `main`/`init` never auto-run in the first
place — only the entry file's do.

Calls can recurse (a class calling itself, directly or through other
classes) up to a fixed depth (currently 1000 in the compiled/`--run` path,
lower in the tree-walking interpreter); exceeding it is a runtime error
rather than a hang or a crash, so unbounded recursion fails cleanly.

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
mentions to *your* file. If `a.el` mentions `b.el`, and `b.el` separately
mentions `c.el`, `a.el` has no way to reach `c.el`'s classes — only
`b.el`'s own `(ment)` classes, under the alias `a.el` gave them. This
holds even though `b.el`'s own class bodies can still freely use `b.el`'s
own `@mentions` — a mentioned file's `@mentions` always resolve using
*that file's own* alias table, regardless of how the file itself was
reached, so a library file that itself depends on other files keeps
working correctly when mentioned by something else.

Two different `@mentions` lines in the same file may not reuse the same
alias for two different files — that's a build-time error. The same file
mentioned (under any alias, from any number of different files) is only
ever read and linked once. A file mentioning itself, or a longer cycle
(A mentions B, B mentions A), is not an error — each file is still only
linked once; the second, cyclic edge is simply a no-op re-entry into a
file already fully linked.

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
and `float` variables. `<expression>` may be a literal, a variable, or an
arithmetic expression; a literal or variable operand must match `<NAME>`'s
declared type exactly — `int` and `float` never mix, even between two
variables (a compile-time (parse) error otherwise). An arithmetic
`<expression>` is runtime-checked instead, same as general arithmetic
elsewhere. `/=` on `int` uses integer (floor) division; on `float` it uses
real division. Dividing by zero is a runtime error either way.

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

### while

```
while (<expression>) {
    <statement>*
}
```

Repeats the block for as long as `<expression>` is truthy, checked before
every iteration (so a false condition means the body never runs). The body
can be empty and can contain anything else the language supports,
including `if`, nested loops, and calling classes. A single optional `;`
is allowed right after the closing `}`.

```
var i: int = 0;
while (i < 3) {
    print(i);
    i += 1;
}
```

### for

```
for (<init>; <condition>; <update>) {
    <statement>*
}
```

A C-style loop: `<init>` runs once, before the first iteration;
`<condition>` is checked before every iteration (a false condition ends
the loop, or skips the body entirely if false from the start);
`<update>` runs after each iteration's body, before the next check of
`<condition>`. Each of `<init>`, `<condition>`, `<update>` is optional and
may be omitted (`for (;;) {}` loops forever unless something inside the
body stops it — evanslang has no `break`/`continue` yet, see "Not yet
implemented").

`<init>` and `<update>` must each be a `var` declaration, a plain
assignment, or a compound assignment — the same statement forms allowed
on their own line elsewhere, just without their own trailing `;` (the
`for(...)`  header's `;`/`)` delimit them instead). A variable declared in
`<init>` is visible for the rest of the enclosing block, the same as any
other `var` (there's no per-loop variable scoping).

```
for (var j: int = 0; j < 3; j += 1) {
    print(j);
}

# the update clause can also use a plain assignment with arithmetic
for (var k: int = 0; k < 3; k = k + 1) {
    print(k);
}

# any clause can be omitted
var i: int = 0;
for (; i < 3;) {
    i += 1;
}
```

### try / catch / throw

```
try {
    <statement>*
}
catch (<NAME>: str) {
    <statement>*
}
```

```
throw <expression>;
```

`try { ... } catch (<NAME>: str) { ... }` runs the `try` block; if any
statement inside it (directly, or anywhere inside a class it calls, no
matter how deeply nested) raises a runtime error — either an explicit
`throw`, or a built-in runtime error such as division by zero, an
arithmetic/comparison type mismatch, or negating a non-numeric value — the
rest of the `try` block is abandoned and the `catch` block runs instead,
with `<NAME>` bound to the error's message as a `str` (`<NAME>: str`
implicitly declares `<NAME>` the same as a `var`, visible for the rest of
the `catch` block). If the `try` block completes without error, `catch`
never runs. There is no `finally`, and `catch` is required — a `try` with
no `catch` is a parse error.

`throw <expression>;` raises a runtime error carrying `<expression>`'s
value as the message. `<expression>` must evaluate to a `str` — throwing a
non-`str` value is a runtime error (`throw` isn't statically type-checked
against a literal string requirement, matching how arithmetic/comparison
operand types are also runtime-only). An uncaught `throw` (or uncaught
built-in error) propagates all the way out and is reported the same as any
other runtime error.

`try`/`catch` can nest, and a `catch` block can itself `throw` (including
rethrowing) to be caught by an enclosing `try`. Errors thrown from deep
inside a chain of called classes correctly unwind back to the nearest
enclosing `try` in the caller, restoring the call stack to where the `try`
began.

```
class risky() {
    var a: int = 10;
    var b: int = 0;
    var result: int = a / b;
}

class main() {
    try {
        risky;
    }
    catch (e: str) {
        print("caught:");
        print(e);
    }

    try {
        throw "something went wrong";
    }
    catch (e: str) {
        print(e);
    }
}
```

### pointers

```
var <NAME>: ptr<type> = &<VARIABLE>;
*<NAME>
*<NAME> = <expression>;
```

`ptr<type>` declares a pointer variable, where `<type>` is one of `int`,
`str`, `float`, `bool` (pointer-to-pointer, `ptr<ptr<...>>`, isn't
supported). `&<VARIABLE>` (address-of) takes a pointer to an existing,
already-declared variable of that same `<type>` — the types must match
exactly, the same as every other `var` initializer. `*<NAME>`
(dereference) reads through the pointer to get the pointee's current
value, usable anywhere an expression is valid; `*<NAME> = <expression>;`
writes through the pointer, mutating the pointee variable itself (not just
the pointer). A pointer variable can be reassigned to point at a different
variable later, the same as any other `var`:

```
var x: int = 10;
var p: ptr<int> = &x;
print(*p);       # 10
*p = 99;
print(x);        # 99 - the write went through to x

var y: int = 5;
p = &y;          # p now points at y instead
*p = 1;
print(y);        # 1
print(x);        # still 99 - x is untouched
```

Dereferencing a variable that isn't a pointer, or a pointer whose declared
pointee type doesn't match how it's used, is a parse-time error — the same
static checking as any other `var`. Reading/writing through a pointer
whose pointee has since gone out of scope isn't a concern yet, since
evanslang has no per-block variable scoping (a `var` lives for the rest of
its enclosing class body, same as everywhere else in the language).
`*<NAME> += <expression>;` (compound assignment through a pointer) isn't
supported yet — use `*<NAME> = *<NAME> + <expression>;` instead.
`print(<pointer>)` (printing the pointer itself, not `*<pointer>`) prints
an opaque `ptr@<address>` marker rather than the pointee's value.

### lists

```
list <NAME>;
list <NAME>: [<expression>, <expression>, ...];
list<type> <NAME>: [<expression>, <expression>, ...];
```

`list <NAME>;` declares an empty list — unlike `var NAME: type;`, it's
immediately usable (`.append(...)`, indexing) rather than having no
storage until first assigned. `list <NAME>: [...];` declares a list with
initial elements; without a `<type>`, elements can be any mix of `int`,
`str`, `float`, `bool` (and later assignments/appends accept anything
too). `list<type> <NAME>: [...];` opts into type-checking: every literal
in the initializer must be `<type>` (checked at parse time), and every
later `.append(...)`/index-assignment is checked at runtime, raising a
clean runtime error on a mismatch.

```
list nums: [1, 2, 3];
print(nums[0]);        # 1
nums[0] = 99;
print(nums);            # [99, 2, 3]
nums.append(4);
print(nums.length());   # 4

list<int> typed: [1, 2, 3];
typed.append("bad");    # runtime error: wrong element type
```

- `<NAME>[<expression>]` — read an element by position (0-indexed). Out of
  range, or a non-`int` index, is a runtime error.
- `<NAME>[<expression>] = <expression>;` — write an element by position.
  Same range/index-type checks as reading.
- `<NAME>.append(<expression>)` — add an element at the end. Usable as an
  expression (it evaluates to the appended value) or as a bare statement.
- `<NAME>.length()` — the number of elements, as an `int`.

Both `.append(...)`/`.length()` and indexing are only valid on a
previously-declared `list` — using them on a non-list variable, or a
declared `list` on a non-`list` variable, is a parse-time error where the
target is a plain identifier (the common case); an index/element-type
mismatch that can't be seen at parse time (e.g. through a non-literal
expression) is instead a runtime error, the same as arithmetic/pointer
type checks elsewhere. `print(<list>)` prints every element
comma-separated inside `[...]`, with `str` elements quoted (`["a", 1,
true]`) so they're distinguishable from other element types in the
output.

### ascii

```
ascii <expression>;
```

Loads the image at the path given by `<expression>` (a `str`, evaluated
the same as any other expression — a string literal or a variable) and
prints it to stdout as ASCII art, scaled to a fixed 80-column width with
the height adjusted to roughly preserve the source image's aspect ratio.
Requires the `pillow` package to be installed (see `requirements.txt`) —
`.png`, `.jpg`, and every other format Pillow supports are accepted. The
path is resolved relative to the current working directory the `evlng`
CLI is run from, not the `.el` file's own location. A missing file, an
unreadable/corrupt image, or a non-`str` expression are all runtime
errors (catchable with `try`/`catch`, the same as any other runtime
error); Pillow not being installed is also a runtime error, only raised
the first time `ascii` actually runs, not at parse or build time.

```
ascii "photo.png";

var path: str = "photo.png";
ascii path;
```

### video

```
video <expression>;
```

Loads the video at the path given by `<expression>` (a `str`, same rules
as `ascii`'s path) and plays it as ASCII art directly in the terminal:
each frame is converted the same way `ascii` converts a still image (same
80-column width, same character ramp), the screen is cleared before each
frame is printed (so it looks like an animation playing in place, not a
wall of scrolling text), and playback is paced to roughly match the
source video's own frame rate. `video <expression>;` blocks until
playback finishes — the statement after it doesn't run until every frame
has played. Requires the `opencv-python` package to be installed (see
`requirements.txt`); `.mp4`, `.avi`, `.mov`, and most other common
container/codec combinations are accepted, since decoding is delegated
entirely to OpenCV. The same error handling as `ascii` applies: a missing
file, an unreadable/corrupt video, or a non-`str` expression are all
catchable runtime errors, as is `opencv-python` not being installed
(raised only the first time `video` actually runs).

```
video "clip.mp4";

var path: str = "clip.mp4";
video path;
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
| `ptr<type>` | A pointer to an `int`/`str`/`float`/`bool` variable | `&x` |
| `list` / `list<type>` | An ordered, mutable collection — `list` allows mixed element types, `list<type>` restricts to one | `[1, 2, 3]` |

`int` and `float` are always distinct — an `int` variable can never hold a
`float` value or vice versa, in `var`, plain assignment, or compound
assignment. There's no automatic widening (e.g. `int` → `float`).
`ptr<type>` is itself a distinct type per pointee `type` (`ptr<int>` and
`ptr<str>` don't mix) — see "pointers" above. `list`/`list<type>` are
declared with their own `list` statement, not `var` — see "lists" above.

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
- Arithmetic: `+`, `-`, `*`, `/` (infix, usable anywhere an expression is
  valid — inside `print(...)`, `var`/assignment initializers, `if`/`while`/
  `for` conditions, compound assignment, etc.) and unary `-` (negation,
  prefix, e.g. `-x`)
- Parenthesized expressions: `(<expression>)`, to override precedence
- `&<VARIABLE>` (address-of, prefix) — see "pointers" above
- `*<expression>` (dereference, prefix) — see "pointers" above
- `<NAME>[<expression>]` (list indexing), `<NAME>.append(<expression>)`,
  `<NAME>.length()` — see "lists" above

Precedence, loosest to tightest: `||`, then `&&`, then `!`, then the
comparison operators, then `+`/`-` (addition/subtraction), then `*`/`/`
(multiplication/division), then unary `-`/`*` (negation/dereference, same
tier), then primaries (literals/identifiers/`input`/parenthesized
expressions/`&<VARIABLE>`). `!` applies to the entire comparison that
follows it (`!a == b` means `!(a == b)`, not `(!a) == b`). Parentheses
group any expression and can be nested, e.g. `(2 + 3) * 4` evaluates to
`20`. Prefix `*` (dereference) is unambiguous with infix `*`
(multiplication) — the parser only ever reads a prefix `*` where an
operand is expected, so `*p + 1` dereferences `p` first, and `a * b`
multiplies as usual.

`+`, `-`, `*`, `/` are not statically type-checked against the variable
they're assigned to beyond requiring an `int` or `float` target — whether
the operands themselves are compatible (e.g. mixing `int` and `str`) is
checked at runtime, raising a clean runtime error, the same as comparisons.
Unary `-` on a non-numeric value (e.g. a `bool`) is also a runtime error.

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
<NAME>.parse(<type>)
```

Converts a `str` variable's current value to `<type>`, one of `int`,
`float`, `bool`, or `str` (a no-op identity conversion). `<NAME>` must be
a previously-declared `str` variable — calling `.parse(...)` on a non-`str`
or undeclared variable is a parse-time error, as is naming an unknown
type. `<type>` must also match whatever the result is assigned or
initialized into — `var f: float = bob.parse(int);` is a parse-time error
because the declared type (`float`) doesn't match the parse target
(`int`), even though both are numeric.

At runtime, `int`/`float` use normal numeric parsing; `bool` accepts
exactly the strings `"true"` or `"false"` (case-sensitive, matching the
literal syntax) and rejects anything else. A string that doesn't match
`<type>` raises a runtime error. `.parse(...)` can be used as an
expression (assigned or passed to `print`) or as a bare statement
(`bob.parse(int);`), in which case the result is simply discarded.

```
var bob: str = "42";
var n: int = bob.parse(int);
print(n);

var pi_str: str = "3.14";
var pi: float = pi_str.parse(float);
print(pi);

var flag_str: str = "true";
var flag: bool = flag_str.parse(bool);
print(flag);
```

## Grammar (informal)

```
program        := mention* classDecl+
mention        := "@" "mentions" filename "->" IDENTIFIER ";"
filename       := IDENTIFIER ("." IDENTIFIER)*
classDecl      := "class" IDENTIFIER "(" "ment"? ")" block ";"?
statement      := printStmt | varDecl | listDecl | assignment | derefAssign
                  | indexAssign | compoundAssign | ifStmt | whileStmt | forStmt
                  | tryStmt | throwStmt | asciiStmt | videoStmt | exprStmt | callStmt
callStmt       := IDENTIFIER ";" | IDENTIFIER "." IDENTIFIER ";"
printStmt      := "print" "(" expression ")" ";"
varDecl        := "var" IDENTIFIER ":" type ("=" expression)? ";"
listDecl       := "list" ("<" elementType ">")? IDENTIFIER (":" listLiteral)? ";"
listLiteral    := "[" (expression ("," expression)*)? "]"
elementType    := "int" | "str" | "float" | "bool"
assignment     := IDENTIFIER "=" expression ";"
derefAssign    := "*" IDENTIFIER "=" expression ";"
indexAssign    := IDENTIFIER "[" expression "]" "=" expression ";"
compoundAssign := IDENTIFIER ("+=" | "-=" | "*=" | "/=") expression ";"
ifStmt         := "if" "(" expression ")" block ";"?
                  ("elseif" "(" expression ")" block ";"?)*
                  ("else" block ";"?)?
whileStmt      := "while" "(" expression ")" block ";"?
forStmt        := "for" "(" forClause? ";" expression? ";" forClause? ")" block ";"?
forClause      := varDecl' | assignment' | compoundAssign'   # same forms, no trailing ";"
tryStmt        := "try" block "catch" "(" IDENTIFIER ":" "str" ")" block ";"?
throwStmt      := "throw" expression ";"
asciiStmt      := "ascii" expression ";"
videoStmt      := "video" expression ";"
exprStmt       := expression ";"    # currently only reachable via IDENTIFIER "." "parse" "(" type ")" | ".append" "(" expression ")"
block          := "{" statement* "}"
type           := "int" | "str" | "float" | "bool" | "ptr" "<" ("int" | "str" | "float" | "bool") ">"
expression     := or
or             := and ("||" and)*
and            := not ("&&" not)*
not            := "!" not | comparison
comparison     := additive (("==" | "!=" | "<" | "<=" | ">" | ">=") additive)?
additive       := multiplicative (("+" | "-") multiplicative)*
multiplicative := unaryPrefix (("*" | "/") unaryPrefix)*
unaryPrefix    := "-" unaryPrefix | "*" unaryPrefix | "&" IDENTIFIER | primary
primary        := STRING | INT | FLOAT | "true" | "false"
                  | IDENTIFIER (parseCall | appendCall | lengthCall | indexExpr)?
                  | inputCall | "(" expression ")"
parseCall      := "." "parse" "(" type ")"
appendCall     := "." "append" "(" expression ")"
lengthCall     := "." "length" "(" ")"
indexExpr      := "[" expression "]"
inputCall      := "input" "(" STRING ")"
```

A file that defines no `class main()` still parses successfully as long
as it has at least one class or mention — it's only rejected (at build
time, not parse time) if it's the file actually being compiled/run.

## Not yet implemented

- Short-circuit evaluation of `&&`/`||`
- `break` / `continue` inside loops
- Functions
- Block comments (`#` only comments to end of line)
- String concatenation with `+`
- Real OOP: fields, methods (beyond a single callable body), `new`/instantiation, `this`, inheritance, parameters, return values — classes are currently just named, callable blocks of statements
- Quoted/path-style `@mentions` filenames (e.g. subdirectories) — the filename is a bare dotted identifier sequence, so it must look like a valid identifier chain (`utils.el`, not `"../lib/utils.el"`)
- `finally` blocks
- Custom/typed exceptions — every thrown or built-in error is just a `str` message; there's no error "kind" to distinguish or match on beyond the message text itself
- Pointer-to-pointer (`ptr<ptr<...>>`)
- Compound assignment through a pointer (`*p += 1;`) — use `*p = *p + 1;` instead
- Pointers into `for`-loop init/update clauses (`for (...; ...; *p = *p + 1) {}`)
- Lists of lists (nested lists), lists of pointers, or `ptr<list>`
- Removing/inserting elements (`.pop()`, `.remove(...)`, `.insert(...)`) — only `.append(...)` exists so far
- List literals/`[i]` indexing/`.append`/`.length` inside `for`-loop init/update clauses, or as a `catch (e: str)` binding target
- Negative list indices (`nums[-1]`) or slicing (`nums[1:3]`)
- Configurable ASCII art width, character ramp, or color output — `ascii`/`video` always render at a fixed 80 columns using a fixed grayscale ramp
- Saving/writing files of any kind — `ascii`/`video` only ever read
- Interrupting/stopping `video` playback early (e.g. `break`, or a keypress) — it always plays every frame to completion
- Audio playback — `video` only renders the visual frames as ASCII art; any audio track is ignored entirely
