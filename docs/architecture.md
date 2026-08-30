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
| `src/lexer/` | `Token`/`TokenType`, and `Lexer` which turns source text into a token stream. |
| `src/nodes/` | AST node classes (`Program`, `PrintStatement`, `VarDecl`, `Assignment`, `InputCall`, `BinaryOp`, `IfStatement`, `StringLiteral`, `IntLiteral`, `Identifier`). Named `nodes` rather than `ast` to avoid shadowing Python's stdlib `ast` module. |
| `src/parser/` | Recursive-descent `Parser` that turns tokens into an AST. Tracks each variable's declared type in `Parser.declared_types` as it parses `var` statements, and uses that table to type-check both initializers and later `Assignment`s at parse time (a mismatch, or an assignment to an undeclared name, is a `ParseError`). `_parse_expression` handles an optional trailing `== primary` on top of `_parse_primary`; equality operands are not type-checked. `_parse_if_statement` parses the `if` branch, then loops on `elseif` and finally an optional `else`, sharing `_parse_block` (`{ statement* }`) across all three; `_skip_optional_semicolon` tolerates (but doesn't require) a `;` after any block. `_parse_compound_assignment` desugars `NAME += expr;` (and `-=`/`*=`/`/=`) into a plain `Assignment(NAME, BinaryOp(op, Identifier(NAME), expr))` at parse time — the VM/interpreter never see a distinct "compound assignment" concept, only the `Assignment` + `BinaryOp` they already handle. |
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
| `PRINT` | Pop the stack and print it. |
| `EQ` | Pop two values, push `left == right`. |
| `ADD` / `SUB` / `MUL` / `DIV` | Pop `right` then `left`, push `left <op> right`. `DIV` uses integer (floor) division and raises `EvansLangError` on division by zero. |
| `JUMP_IF_FALSE <offset>` | Pop a value; if falsy, add `offset` to the program counter (`offset` is relative to this instruction's own index, so `+1` means "the next instruction"). |
| `JUMP <offset>` | Unconditionally add `offset` to the program counter. Emitted at the end of each `if`/`elseif` branch body to skip past the remaining branches and any `else` once a branch has run. |
| `HALT` | Stop execution. |

`var NAME: type;` (no initializer) generates no instructions — the variable
has no entry in the VM's `variables` dict until an `Assignment` (`STORE`)
actually runs. Reading it before that point behaves the same as reading any
other undefined variable (`LOAD` raises `EvansLangError`).

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
