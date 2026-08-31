# evanslang architecture

## Pipeline

```
root source (.el)
   |
   v
Lexer + Parser   src/lexer/, src/parser/   -> AST (nodes.Program), per file
   |
   v
Linker           src/linker/link()   -> ResolvedProgram (recursively parses
   |                                     every @mentions-ed file too, merges
   |                                     their (ment) classes under alias::name
   |                                     qualified keys, into one flat namespace)
   v
CodeGenerator    src/codegen/        -> IR (ir.Program, a flat list of bytecode
   |                                     Instructions, one CALL-able block per class)
   v
bytecode_file    src/vm/bytecode_file.py  -> serialized binary (--build output)
   |
   v
VM               src/vm/vm.py        -> executes the IR (--run)
```

There's also a tree-walking `Interpreter` (`src/interpreter/interpreter.py`)
that executes the AST directly (via `ResolvedProgram`, same as codegen),
skipping codegen/bytecode entirely. It's kept in sync with the VM's
behavior but is not currently wired into the CLI.

## CLI (`evlng`)

`bin/evlng` is a thin shell wrapper around `src/main.py`.

- `evlng --build SOURCE OUTPUT` — link (parse `SOURCE` plus every file it
  transitively `@mentions`) and codegen the result, writing serialized
  bytecode to `OUTPUT` (a `.evlc` extension is appended automatically if
  `OUTPUT` doesn't already end in `.evlc`).
- `evlng --run BINARY` — deserialize `BINARY` and execute it on the `VM`. If
  `BINARY` doesn't exist as given, `BINARY.evlc` is tried as a fallback, so
  `evlng --run hello` works after `evlng --build hello.el hello`.

## Modules

| Path | Responsibility |
|------|-----------------|
| `src/lexer/` | `Token`/`TokenType`, and `Lexer` which turns source text into a token stream. `_skip_whitespace` also skips `#`-to-end-of-line comments (via `_skip_comment`), looping so whitespace and comments can alternate; comments never produce a token, so the parser never sees them. `_read_number` (formerly `_read_int`) reads digits, then — only if a `.` is immediately followed by another digit — continues reading a `FLOAT` token; a bare trailing `.` with no digit after it is left alone (not consumed), since `.` isn't valid syntax anywhere else. A standalone `.` (e.g. after an identifier, as in `bob.parse`) lexes as its own `DOT` token. `true`/`false` are not their own token type — they lex as plain `IDENTIFIER`, the same as `input`, `var`, `if`, etc., and are special-cased in `Parser._parse_primary`. `@` and `->` (`AT`, `ARROW`) exist solely for `@mentions` directives; `->` is unambiguous with `-=` since `-` alone otherwise has no meaning. |
| `src/nodes/` | AST node classes (`Program`, `ClassDecl`, `Mention`, `CallStatement`, `PrintStatement`, `ExpressionStatement`, `VarDecl`, `Assignment`, `InputCall`, `ParseCall`, `BinaryOp`, `UnaryOp`, `IfStatement`, `StringLiteral`, `IntLiteral`, `FloatLiteral`, `BoolLiteral`, `Identifier`). Named `nodes` rather than `ast` to avoid shadowing Python's stdlib `ast` module. `Program` holds `classes: dict[str, ClassDecl]` (keyed by class name, within one file) and `mentions: list[Mention]` — there is no flat top-level statement list any more; every statement lives inside some `ClassDecl.body`. |
| `src/parser/` | Recursive-descent `Parser` that turns one file's tokens into an AST. `parse()` first calls `_prescan_names()` — a single linear pass over the top-level tokens (tracking `{`/`}` depth so it only looks at depth 0) that collects every class name and `@mentions` alias *before* real parsing begins. This is what lets a class body call another class declared later in the same file, or `alias.NAME;` calls resolve against an alias declared anywhere in the file — without it, forward references would fail since a statement is parsed before the parser has seen the later `class` keyword. After the prescan, `parse()` reads `mention*` then `class*` via `_parse_mention`/`_parse_class`; a file needs at least one class or mention to parse, but does *not* need a `class main()` — that check is the linker's job (see below), since a file might only ever be `@mentions`-ed, never run directly. Tracks each variable's declared type in `Parser.declared_types` as it parses `var` statements, and uses that table to type-check both initializers and later `Assignment`s at parse time (a mismatch, or an assignment to an undeclared name, is a `ParseError`). Expression parsing is a standard precedence chain: `_parse_expression` (`\|\|`) → `_parse_and` (`&&`) → `_parse_unary_not` (prefix `!`, recursive so `!!a` works) → `_parse_comparison` (`==`, `!=`, `<`, `<=`, `>`, `>=`, all non-associative — one comparison per expression, no chaining like `a < b < c`) → `_parse_primary`. None of the comparison/boolean operators are type-checked at parse time; `<`/`<=`/`>`/`>=` are checked at runtime instead (see Error handling). `_parse_if_statement` parses the `if` branch, then loops on `elseif` and finally an optional `else`, sharing `_parse_block` (`{ statement* }`) across all three; `_skip_optional_semicolon` tolerates (but doesn't require) a `;` after any block. `_parse_compound_assignment` desugars `NAME += expr;` (and `-=`/`*=`/`/=`) into a plain `Assignment(NAME, BinaryOp(op, Identifier(NAME), expr))` at parse time — the VM/interpreter never see a distinct "compound assignment" concept, only the `Assignment` + `BinaryOp`/`UnaryOp` they already handle. `int` and `float` are enforced as strictly non-interchangeable everywhere a type is checked (`_check_type`, `_parse_compound_assignment`'s `literal_types` map keyed by declared type) — no widening either direction. `_parse_primary` handles `IDENTIFIER "." "parse"` by wrapping the identifier in a `ParseCall`, after checking `declared_types` confirms the target is a declared `str` (a parse-time error otherwise, since parsing a non-`str` never makes sense); `_check_type` treats `ParseCall` as valid for both `int` and `float`, since the actual numeric type is only knowable once the string is parsed at runtime. `_parse_statement` distinguishes three different meanings of `IDENTIFIER "."` by checking `mention_aliases`/`class_names` (populated by the prescan) *before* falling back to `.parse`: `alias.NAME;` (alias is a known mention) → `_parse_call_statement`; `str_var.parse` → `_parse_expression_statement` wrapping a `ParseCall`; bare `NAME;` where `NAME` is a known class → also `_parse_call_statement`. |
| `src/linker/` | New module. `link(root_path)` recursively resolves `@mentions`: parses the root file, then for each `Mention` parses the target file (resolved relative to the *mentioning* file's directory, not the root or cwd) and merges its classes into one flat `dict[str, ClassDecl]` — local classes keep their bare name, a mentioned file's classes are namespaced as `f"{alias}{SEPARATOR}{name}"` (`SEPARATOR = "::"`) and only included if `class_decl.is_ment` is true; non-`ment` classes in a mentioned file are simply skipped, which is what makes them invisible from outside their own file. Recursion is **not** transitive from the importer's perspective — if A mentions B and B mentions C, A never sees `c::deep`-shaped keys; B's own call to `c.deep` resolves fine because B's *own* parse recorded `c` as one of *its* mention aliases, and that resolution happens when B's classes are being linked in, using B's aliasing, not A's. A `visiting: list[Path]` stack (resolved absolute paths) detects cycles and raises `EvansLangError` with the full chain. `link()` raises if the *root* file's merged class set has no `"main"` — mentioned-only library files are exempt from that check since `Parser.parse()` never enforced it on them to begin with. Returns a `ResolvedProgram(classes, entry="main")`, the type codegen and the interpreter both consume instead of a raw `Program`. |
| `src/ir/` | `OpCode` enum and `Instruction`/`Program` (bytecode) types. Includes `CALL`/`RETURN` for class calls. |
| `src/codegen/` | `CodeGenerator.generate(resolved: ResolvedProgram)`: compiles every class body into its own instruction block (each ending in `RETURN`), lays every block out one after another following a small prologue, then patches every `CALL`'s operand from the target class's qualified name (a placeholder string at emission time) to that block's absolute starting index once every block's position is known. See "Multi-class codegen" below. |
| `src/vm/` | `VM` (stack-based bytecode interpreter with a variable dict and a `call_stack` list of return addresses) and `bytecode_file` (binary serialization format for `--build`/`--run`). |
| `src/interpreter/` | `Interpreter`: direct AST tree-walker, alternative to the VM path. `run(resolved: ResolvedProgram)` runs `init` (if present) then `entry`, both via `_run_class(name)`, which looks the class up in `resolved.classes` and executes its body statement-by-statement — the interpreter's version of the VM's call/return, but as a plain recursive Python call rather than an explicit stack. |
| `src/semantic/` | Reserved for a dedicated semantic-analysis pass (symbol table, type checking) as the language grows past parser-level checks. Currently empty. |
| `src/utils/errors.py` | `EvansLangError` and subclasses (`LexError`, `ParseError`) used for user-facing diagnostics. Each carries structured `message`/`line`/`column`/`kind` fields (rather than a single pre-formatted string) so `main.py` can render them. Linker errors (missing file, circular import, missing entry point) and codegen errors (call to a class that doesn't exist or isn't `ment`) raise a bare `EvansLangError` — they have no source line/column since they describe a whole-file or whole-program condition, not a single token. |

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
| `CALL <addr>` | Push `pc + 1` onto `call_stack`, then jump to `addr`. Unlike `JUMP`/`JUMP_IF_FALSE`, `addr` is **absolute**, not relative — a class can be called from many different call sites, so a fixed relative offset wouldn't make sense; codegen resolves the true absolute address only after every class's block position is known (see "Multi-class codegen"). |
| `RETURN` | Pop an address off `call_stack` and jump there. Raises `EvansLangError` ("Return with no active call") if the call stack is empty — not reachable through normal codegen output, since every compiled class body ends in exactly one `RETURN` matching the `CALL` that invoked it. |
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

### Multi-class codegen

`CodeGenerator.generate()` works in three passes over `resolved.classes`
(a flat `dict[str, ClassDecl]` keyed by qualified name — `"main"`,
`"helper"`, `"test::sdgdsg"`, etc. — already produced by the linker):

1. **Compile each class independently.** Every class's body is compiled
   into its own `list[Instruction]` exactly as before (reusing
   `_generate_statement`/`_generate_expression` unchanged), with a
   `RETURN` appended at the end. At this point a `CallStatement` compiles
   to `Instruction(OpCode.CALL, target)` where `target` is still the
   *qualified name string* (`node.name`, or `f"{node.alias}{SEPARATOR}{node.name}"`)
   — not yet an address, since block positions aren't known until step 2.
2. **Lay out and record start positions.** A small prologue is prepended:
   `CALL "init"` (only if an `"init"` class exists), then `CALL <entry>`,
   then `HALT`. Every compiled class block is then concatenated after the
   prologue in dict-iteration order, recording `block_starts[name] = <index>`
   as each one is placed.
3. **Patch every CALL.** A final pass walks the fully-assembled
   instruction list and replaces each `CALL`'s string operand with
   `block_starts[target]` — the target's actual absolute position. A
   target that isn't in `block_starts` (an unmentioned class, a typo, or
   a class that exists in the mentioned file but isn't `(ment)`) raises
   `EvansLangError` here, with a specifically-worded message for the
   `alias::name` case pointing at what to fix.

Because every class compiles to a self-contained block ending in
`RETURN`, and every call site is a `CALL` to that block's absolute start,
the same class can be called from arbitrarily many places (including
itself, recursively, or two different classes both calling it) without
any code duplication — this is the payoff of implementing real `CALL`/
`RETURN` with a VM call stack instead of inlining bodies at each call
site.
