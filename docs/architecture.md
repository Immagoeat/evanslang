# evanslang architecture

## Pipeline

```
source (.el)
   |
   v
Lexer            src/lexer/          -> list[Token]
   |
   v
Parser           src/parser/         -> AST (nodes.Program)
   |
   v
CodeGenerator    src/codegen/        -> IR (ir.Program, a flat list of bytecode Instructions)
   |
   v
bytecode_file    src/vm/bytecode_file.py  -> serialized binary (--build output)
   |
   v
VM               src/vm/vm.py        -> executes the IR (--run)
```

There's also a tree-walking `Interpreter` (`src/interpreter/interpreter.py`)
that executes the AST directly, skipping codegen/bytecode entirely. It's kept
in sync with the VM's behavior but is not currently wired into the CLI.

## CLI (`evlng`)

`bin/evlng` is a thin shell wrapper around `src/main.py`.

- `evlng --build SOURCE OUTPUT` — lex, parse, and codegen `SOURCE`, writing
  serialized bytecode to `OUTPUT` (a `.evlc` extension is appended
  automatically if `OUTPUT` doesn't already end in `.evlc`).
- `evlng --run BINARY` — deserialize `BINARY` and execute it on the `VM`. If
  `BINARY` doesn't exist as given, `BINARY.evlc` is tried as a fallback, so
  `evlng --run hello` works after `evlng --build hello.el hello`.

## Modules

| Path | Responsibility |
|------|-----------------|
| `src/lexer/` | `Token`/`TokenType`, and `Lexer` which turns source text into a token stream. `_skip_whitespace` also skips `#`-to-end-of-line comments (via `_skip_comment`), looping so whitespace and comments can alternate; comments never produce a token, so the parser never sees them. `_read_number` (formerly `_read_int`) reads digits, then — only if a `.` is immediately followed by another digit — continues reading a `FLOAT` token; a bare trailing `.` with no digit after it is left alone (not consumed), since `.` isn't valid syntax anywhere else. A standalone `.` (e.g. after an identifier, as in `bob.parse`) lexes as its own `DOT` token. `true`/`false` are not their own token type — they lex as plain `IDENTIFIER`, the same as `input`, `var`, `if`, etc., and are special-cased in `Parser._parse_primary`. |
| `src/nodes/` | AST node classes (`Program`, `PrintStatement`, `ExpressionStatement`, `VarDecl`, `Assignment`, `InputCall`, `ParseCall`, `BinaryOp`, `UnaryOp`, `IfStatement`, `StringLiteral`, `IntLiteral`, `FloatLiteral`, `BoolLiteral`, `Identifier`). Named `nodes` rather than `ast` to avoid shadowing Python's stdlib `ast` module. |
| `src/parser/` | Recursive-descent `Parser` that turns tokens into an AST. `parse()` (the entry point) requires the source to start with `class main() { ... }` and end there — anything before, after, or instead of that block is a `ParseError`; the block's contents (via `_parse_block`, shared with `if`/`elseif`/`else`) become `Program.statements` directly, so nothing downstream (codegen, VM, interpreter) knows `class main` exists — `Program`'s shape is unchanged. Tracks each variable's declared type in `Parser.declared_types` as it parses `var` statements, and uses that table to type-check both initializers and later `Assignment`s at parse time (a mismatch, or an assignment to an undeclared name, is a `ParseError`). Expression parsing is a standard precedence chain: `_parse_expression` (`\|\|`) → `_parse_and` (`&&`) → `_parse_unary_not` (prefix `!`, recursive so `!!a` works) → `_parse_comparison` (`==`, `!=`, `<`, `<=`, `>`, `>=`, all non-associative — one comparison per expression, no chaining like `a < b < c`) → `_parse_primary`. None of the comparison/boolean operators are type-checked at parse time; `<`/`<=`/`>`/`>=` are checked at runtime instead (see Error handling). `_parse_if_statement` parses the `if` branch, then loops on `elseif` and finally an optional `else`, sharing `_parse_block` (`{ statement* }`) across all three; `_skip_optional_semicolon` tolerates (but doesn't require) a `;` after any block. `_parse_compound_assignment` desugars `NAME += expr;` (and `-=`/`*=`/`/=`) into a plain `Assignment(NAME, BinaryOp(op, Identifier(NAME), expr))` at parse time — the VM/interpreter never see a distinct "compound assignment" concept, only the `Assignment` + `BinaryOp`/`UnaryOp` they already handle. `int` and `float` are enforced as strictly non-interchangeable everywhere a type is checked (`_check_type`, `_parse_compound_assignment`'s `literal_types` map keyed by declared type) — no widening either direction. `_parse_primary` handles `IDENTIFIER "." "parse"` by wrapping the identifier in a `ParseCall`, after checking `declared_types` confirms the target is a declared `str` (a parse-time error otherwise, since parsing a non-`str` never makes sense); `_check_type` treats `ParseCall` as valid for both `int` and `float`, since the actual numeric type is only knowable once the string is parsed at runtime. `_parse_statement` falls through to `_parse_expression_statement` when it sees `IDENTIFIER "."`, wrapping the parsed expression in an `ExpressionStatement` so a bare `bob.parse;` (result unused) is valid syntax, not just `.parse` used as an initializer/assigned value. |
| `src/ir/` | `OpCode` enum and `Instruction`/`Program` (bytecode) types. |
| `src/codegen/` | `CodeGenerator`: AST -> IR. |
| `src/vm/` | `VM` (stack-based bytecode interpreter with a variable dict) and `bytecode_file` (binary serialization format for `--build`/`--run`). |
| `src/interpreter/` | `Interpreter`: direct AST tree-walker, alternative to the VM path. |
| `src/semantic/` | Reserved for a dedicated semantic-analysis pass (symbol table, type checking) as the language grows past parser-level checks. Currently empty. |
| `src/utils/errors.py` | `EvansLangError` and subclasses (`LexError`, `ParseError`) used for user-facing diagnostics. Each carries structured `message`/`line`/`column`/`kind` fields (rather than a single pre-formatted string) so `main.py` can render them. |

## Bytecode file format

Written by `src/vm/bytecode_file.py`:

```
4 bytes   magic:   b"EVLC"
1 byte    version: currently 1
remainder pickled list[Instruction]
```

Not intended to be stable across versions yet — `version` exists so future
format changes can be detected and rejected cleanly.

By convention, compiled binaries use the `.evlc` extension (see CLI section
above); `.gitignore` excludes `*.evlc` so build output isn't committed.

## Error handling

All user-facing errors (bad syntax, type mismatches, undefined variables)
raise a subclass of `EvansLangError`, carrying `kind` (`"lex error"`,
`"parse error"`, or the base `"error"` for runtime errors with no source
location), `message`, and optional `line`/`column`. `main.py` catches these
at the CLI boundary and renders them with `print_error()`: a bold-red
`<kind>: <message>` header, plus a dim `at <file>:<line>:<column>` line
when a location is available (omitted for runtime errors, which have none),
then exits with status 1. Non-`EvansLangError` failures (`OSError`,
`ValueError` — e.g. a missing source file) are wrapped in a bare
`EvansLangError` so they go through the same renderer.

Color is enabled only when stderr is a TTY (`sys.stderr.isatty()`) and the
`NO_COLOR` environment variable is unset, so piped output, redirected logs,
and CI stay plain-text.

## Current opcodes

| Opcode | Effect |
|--------|--------|
| `PUSH_CONST <value>` | Push a literal onto the stack. |
| `STORE <name>` | Pop the stack, store into variable `name`. |
| `LOAD <name>` | Push the value of variable `name` (error if undefined). |
| `INPUT` | Pop a prompt string, call `input(prompt)`, push the result. |
| `PARSE` | Pop a string, try `int(text)`, fall back to `float(text)`; raises `EvansLangError` if neither succeeds. Push the result. |
| `POP` | Pop and discard the top of the stack. Emitted for `ExpressionStatement` (e.g. a bare `bob.parse;`) so the produced value doesn't linger on the stack. |
| `PRINT` | Pop the stack and print it. |
| `EQ` / `NEQ` | Pop two values, push `left == right` / `left != right`. No type-checking — comparing an `int` to a `str` is allowed. |
| `LT` / `LTE` / `GT` / `GTE` | Pop two values, push `left <op> right` using Python's native ordering comparison. Raises `EvansLangError` if the operand types aren't comparable (e.g. `int` vs `str`), via `VM._compare()`. |
| `AND` / `OR` | Pop two values, push `bool(left) and bool(right)` / `bool(left) or bool(right)`. Both operands are always evaluated by codegen before the opcode runs — no short-circuiting. |
| `NOT` | Pop one value, push `not value`. |
| `ADD` / `SUB` / `MUL` / `DIV` | Pop `right` then `left`, push `left <op> right`. `DIV` checks the runtime Python types of both operands: floor division (`//`) if both are `int`, real division (`/`) otherwise (i.e. either operand is a `float`); raises `EvansLangError` on division by zero either way. |
| `JUMP_IF_FALSE <offset>` | Pop a value; if falsy, add `offset` to the program counter (`offset` is relative to this instruction's own index, so `+1` means "the next instruction"). |
| `JUMP <offset>` | Unconditionally add `offset` to the program counter. Emitted at the end of each `if`/`elseif` branch body to skip past the remaining branches and any `else` once a branch has run. |
| `HALT` | Stop execution. |

`var NAME: type;` (no initializer) generates no instructions — the variable
has no entry in the VM's `variables` dict until an `Assignment` (`STORE`)
actually runs. Reading it before that point behaves the same as reading any
other undefined variable (`LOAD` raises `EvansLangError`).

### bool representation

There's no distinct evanslang runtime value for `bool` — the VM and
interpreter both use Python's native `bool`, which is a subclass of `int`
(`isinstance(True, int)` is `True`). This is invisible in practice because
`bool` values only ever originate from `BoolLiteral`/comparison/boolean
opcodes and are never produced by arithmetic, so the `int`/`bool` overlap
doesn't leak into user-visible behavior. The one place it's handled
explicitly is display: `VM`'s and `Interpreter`'s private `_display()`
helpers check `isinstance(value, bool)` *before* any `int` handling and
render `"true"`/`"false"` instead of Python's `print()` default of
`True`/`False`. `PRINT` (and `print()` in `Interpreter._execute`) always
routes through `_display()`.

### if/elseif/else codegen

`CodeGenerator._generate_if` treats the `if` condition plus every `elseif`
as a uniform list of `(condition, body)` branches, and lays each one out as:

```
condition...
JUMP_IF_FALSE <skip past body + JUMP>
body...
JUMP <skip to end of the whole chain>       (omitted on the last branch when there's no else)
```

followed by the `else` body (if any) with no guard, since reaching it means
every branch above evaluated false. All jump offsets are computed relative
to the jump instruction's own index — `JUMP_IF_FALSE`'s target is computed
first (it only needs to know its own branch's length), and each branch's
trailing `JUMP` is emitted with a placeholder `operand=None` and patched in
a second pass, once the length of every later branch and the `else` body is
known. Because offsets are always relative rather than absolute, nested
`if` blocks compose correctly without any global position bookkeeping. The
VM's `run()` loop uses an explicit program counter (`pc`) rather than
iterating instructions directly, specifically to support these jumps.
