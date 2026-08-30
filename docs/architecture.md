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
| `src/nodes/` | AST node classes (`Program`, `PrintStatement`, `VarDecl`, `Assignment`, `InputCall`, `StringLiteral`, `IntLiteral`, `Identifier`). Named `nodes` rather than `ast` to avoid shadowing Python's stdlib `ast` module. |
| `src/parser/` | Recursive-descent `Parser` that turns tokens into an AST. Tracks each variable's declared type in `Parser.declared_types` as it parses `var` statements, and uses that table to type-check both initializers and later `Assignment`s at parse time (a mismatch, or an assignment to an undeclared name, is a `ParseError`). |
| `src/ir/` | `OpCode` enum and `Instruction`/`Program` (bytecode) types. |
| `src/codegen/` | `CodeGenerator`: AST -> IR. |
| `src/vm/` | `VM` (stack-based bytecode interpreter with a variable dict) and `bytecode_file` (binary serialization format for `--build`/`--run`). |
| `src/interpreter/` | `Interpreter`: direct AST tree-walker, alternative to the VM path. |
| `src/semantic/` | Reserved for a dedicated semantic-analysis pass (symbol table, type checking) as the language grows past parser-level checks. Currently empty. |
| `src/utils/errors.py` | `EvansLangError` and subclasses (`LexError`, `ParseError`) used for user-facing diagnostics. |

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
raise a subclass of `EvansLangError`. `main.py` catches these at the CLI
boundary, prints the message to stderr, and exits with status 1.

## Current opcodes

| Opcode | Effect |
|--------|--------|
| `PUSH_CONST <value>` | Push a literal onto the stack. |
| `STORE <name>` | Pop the stack, store into variable `name`. |
| `LOAD <name>` | Push the value of variable `name` (error if undefined). |
| `INPUT` | Pop a prompt string, call `input(prompt)`, push the result. |
| `PRINT` | Pop the stack and print it. |
| `HALT` | Stop execution. |

`var NAME: type;` (no initializer) generates no instructions — the variable
has no entry in the VM's `variables` dict until an `Assignment` (`STORE`)
actually runs. Reading it before that point behaves the same as reading any
other undefined variable (`LOAD` raises `EvansLangError`).
