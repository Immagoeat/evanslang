# evanslang architecture

## Pipeline

```
root source (.el)
   |
   v
Lexer + Parser   src/lexer/, src/parser/   -> AST (nodes.Program), per file
   |
   v
Linker           src/linker/link()   -> ResolvedProgram (parses every
   |                                     directly @mentions-ed file, each
   |                                     into its own private scope keyed by
   |                                     resolved path, and resolves every
   |                                     CallStatement's target using the
   |                                     alias table of whichever file it
   |                                     was parsed in - not transitive)
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
| `src/nodes/` | AST node classes (`Program`, `ClassDecl`, `Mention`, `CallStatement`, `PrintStatement`, `ExpressionStatement`, `VarDecl`, `Assignment`, `InputCall`, `ParseCall`, `BinaryOp`, `UnaryOp`, `IfStatement`, `WhileStatement`, `ForStatement`, `StringLiteral`, `IntLiteral`, `FloatLiteral`, `BoolLiteral`, `Identifier`). Named `nodes` rather than `ast` to avoid shadowing Python's stdlib `ast` module. `Program` holds `classes: dict[str, ClassDecl]` (keyed by class name, within one file) and `mentions: list[Mention]` — there is no flat top-level statement list any more; every statement lives inside some `ClassDecl.body`. `ForStatement.init`/`.condition`/`.update` are each `Node | None`, since every clause of a C-style `for(...)` header is individually optional. |
| `src/parser/` | Recursive-descent `Parser` that turns one file's tokens into an AST. `parse()` first calls `_prescan_names()` — a single linear pass over the top-level tokens (tracking `{`/`}` depth so it only looks at depth 0) that collects every class name and `@mentions` alias *before* real parsing begins. This is what lets a class body call another class declared later in the same file, or `alias.NAME;` calls resolve against an alias declared anywhere in the file — without it, forward references would fail since a statement is parsed before the parser has seen the later `class` keyword. After the prescan, `parse()` reads `mention*` then `class*` via `_parse_mention`/`_parse_class`; a file needs at least one class or mention to parse, but does *not* need a `class main()` — that check is the linker's job (see below), since a file might only ever be `@mentions`-ed, never run directly. Tracks each variable's declared type in `Parser.declared_types` as it parses `var` statements, and uses that table to type-check both initializers and later `Assignment`s at parse time (a mismatch, or an assignment to an undeclared name, is a `ParseError`). Expression parsing is a standard precedence chain: `_parse_expression` (`\|\|`) → `_parse_and` (`&&`) → `_parse_unary_not` (prefix `!`, recursive so `!!a` works) → `_parse_comparison` (`==`, `!=`, `<`, `<=`, `>`, `>=`, all non-associative — one comparison per expression, no chaining like `a < b < c`) → `_parse_primary`. None of the comparison/boolean operators are type-checked at parse time; `<`/`<=`/`>`/`>=` are checked at runtime instead (see Error handling). `_parse_if_statement` parses the `if` branch, then loops on `elseif` and finally an optional `else`, sharing `_parse_block` (`{ statement* }`) across all three; `_skip_optional_semicolon` tolerates (but doesn't require) a `;` after any block. `_parse_while_statement` is a thin wrapper around the same `_parse_block` machinery. `_parse_for_statement` parses `(`, then each of `init`/`condition`/`update` only if the next token isn't the delimiter that would end that clause (`;`, `;`, `)` respectively), so all three are independently optional (`for (;;) {}` parses fine). `init`/`update` reuse `_parse_var_decl`/`_parse_assignment`/`_parse_compound_assignment` with a `consume_semicolon: bool = True` parameter (`False` from the `for` header, since the header's own `;`/`)` delimits the clause instead of the statement's usual trailing `;`) — this is the only reason those three methods take that parameter at all; every other call site uses the default. `_parse_compound_assignment` desugars `NAME += expr;` (and `-=`/`*=`/`/=`) into a plain `Assignment(NAME, BinaryOp(op, Identifier(NAME), expr))` at parse time — the VM/interpreter never see a distinct "compound assignment" concept, only the `Assignment` + `BinaryOp`/`UnaryOp` they already handle. `int` and `float` are enforced as strictly non-interchangeable everywhere a type is checked (`_check_type`, `_parse_compound_assignment`'s `literal_types` map keyed by declared type) — no widening either direction. `_parse_primary` handles `IDENTIFIER "." "parse" "(" type ")"` by requiring `declared_types` confirms the target is a declared `str` (a parse-time error otherwise, since parsing a non-`str` never makes sense), then requiring the parenthesized argument be one of `VALID_TYPES` (`ParseError` on an unknown type name), producing `ParseCall(target, target_type)`; `_check_type` compares `value.target_type` directly against the declared type of whatever the call is assigned/initialized into (exact match required — `var f: float = s.parse(int);` is a `ParseError` even though both sides are numeric, since `ParseCall` now always carries a concrete, known type rather than the pre-`(type)` design where it was accepted for both `int` and `float` because the real type wasn't knowable until runtime). `_parse_statement` distinguishes three different meanings of `IDENTIFIER "."` by checking `mention_aliases`/`class_names` (populated by the prescan) *before* falling back to `.parse`: `alias.NAME;` (alias is a known mention) → `_parse_call_statement`; `str_var.parse(type)` → `_parse_expression_statement` wrapping a `ParseCall`; bare `NAME;` where `NAME` is a known class → also `_parse_call_statement`. `_parse_call_statement` rejects an unaliased call to a name in `RESERVED_CLASS_NAMES = {"main", "init"}` (a `ParseError`, since both already run automatically — see "call depth guard" in the opcode section below); the check only applies to the local, unaliased form, since a *mentioned* file's `main`/`init` never auto-run and so can't double-run from an explicit `alias.main;`/`alias.init;` call. |
| `src/linker/` | `link(root_path)` resolves `@mentions` and produces a `ResolvedProgram`. Each linked file gets a **scope**: its own resolved (absolute) `Path`, used both as the namespace prefix for its classes (`f"{path}{SEPARATOR}{name}"`, `SEPARATOR = "::"`) and as the key into two shared dicts threaded through the recursion — `classes` (every class from every linked file, keyed by scope) and `ment_by_scope` (`{scope: {class_name: is_ment}}`). The root file is the one exception: its own classes keep bare names (`_qualify` special-cases `scope == root_scope`), so `class main() {}` stays reachable as `"main"`. `_link_file` links a file **once**: it records `ment_by_scope[path]` immediately (before recursing), then processes that file's own `@mentions` (each target gets `_link_file`'d — skipped via `if path in ment_by_scope: return` if some other edge in the graph already linked it), then resolves every `CallStatement` in that file's own class bodies via `_resolve_calls_in_body`, which walks into `if`/`elseif`/`else`/`while`/`for` bodies (via `_statements_in`) to find calls nested arbitrarily deep. A local call (`NAME;`, `node.alias is None`) resolves to `_qualify(scope, ..., name)` — the *current* file's own scope. An aliased call (`alias.NAME;`) looks `node.alias` up in *that file's own* `alias_scopes` dict (built from *that file's own* `@mentions` lines, not the caller's) to find the target file's scope, then checks `ment_by_scope[target_scope][name]` before allowing it — reaching a non-`ment` class via an alias is an `EvansLangError` right here, at link time, not deferred to codegen. Each `CallStatement.resolved_target` is set to the final qualified string; codegen/interpreter read it directly rather than re-deriving it (previously both had their own copy of the qualification logic, which produced the wrong scope whenever a call reached into a file linked in under a different path than the literal alias text implied — this per-file alias scoping is what makes `docs/language_spec.md`'s "`@mentions` only sees classes declared directly in the file it names" hold even when a mentioned file's own class bodies use *that file's own* `@mentions`). Two `@mentions` lines in the same file reusing one alias for two different files is a link-time error (`alias_scopes` rejects the second one). `link()` raises if the *root* file's class set has no `"main"` — mentioned-only library files are exempt, since `Parser.parse()` never required it of them. |
| `src/ir/` | `OpCode` enum and `Instruction`/`Program` (bytecode) types. Includes `CALL`/`RETURN` for class calls. |
| `src/codegen/` | `CodeGenerator.generate(resolved: ResolvedProgram)`: compiles every class body into its own instruction block (each ending in `RETURN`), lays every block out one after another following a small prologue, then patches every `CALL`'s operand from the target class's qualified name (a placeholder string at emission time) to that block's absolute starting index once every block's position is known. See "Multi-class codegen" below. |
| `src/vm/` | `VM` (stack-based bytecode interpreter with a variable dict and a `call_stack` list of return addresses) and `bytecode_file` (binary serialization format for `--build`/`--run`). |
| `src/interpreter/` | `Interpreter`: direct AST tree-walker, alternative to the VM path. `run(resolved: ResolvedProgram)` runs `init` (if present) then `entry`, both via `_run_class(name)`, which looks the class up in `resolved.classes` and executes its body statement-by-statement — the interpreter's version of the VM's call/return, but as a plain recursive Python call (guarded by a `call_depth` counter, see "call depth guard" below) rather than an explicit stack. A `CallStatement`'s target is read directly from `node.resolved_target` (set by the linker), the same as codegen. |
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
| `PARSE <target_type>` | Pop a string, convert it to `target_type` (`"int"`, `"float"`, `"bool"`, or `"str"`) via `utils.runtime.parse_as` — `str` is the identity; `bool` accepts exactly `"true"`/`"false"`; `int`/`float` use normal numeric parsing. Raises `EvansLangError` if the string doesn't match `target_type`. Push the result. |
| `POP` | Pop and discard the top of the stack. Emitted for `ExpressionStatement` (e.g. a bare `bob.parse(int);`) so the produced value doesn't linger on the stack. |
| `PRINT` | Pop the stack and print it. |
| `EQ` / `NEQ` | Pop two values, push `left == right` / `left != right`. No type-checking — comparing an `int` to a `str` is allowed. |
| `LT` / `LTE` / `GT` / `GTE` | Pop two values, push `left <op> right` using Python's native ordering comparison. Raises `EvansLangError` if the operand types aren't comparable (e.g. `int` vs `str`), via `VM._compare()`. |
| `AND` / `OR` | Pop two values, push `bool(left) and bool(right)` / `bool(left) or bool(right)`. Both operands are always evaluated by codegen before the opcode runs — no short-circuiting. |
| `NOT` | Pop one value, push `not value`. |
| `ADD` / `SUB` / `MUL` / `DIV` | Pop `right` then `left`, push `left <op> right`. `DIV` checks the runtime Python types of both operands: floor division (`//`) if both are `int`, real division (`/`) otherwise (i.e. either operand is a `float`); raises `EvansLangError` on division by zero either way. |
| `JUMP_IF_FALSE <offset>` | Pop a value; if falsy, add `offset` to the program counter (`offset` is relative to this instruction's own index, so `+1` means "the next instruction"). |
| `JUMP <offset>` | Unconditionally add `offset` to the program counter. Emitted at the end of each `if`/`elseif` branch body to skip past the remaining branches and any `else` once a branch has run. |
| `CALL <addr>` | If `call_stack` is already `MAX_CALL_DEPTH` (1000) deep, raises `EvansLangError` rather than recursing further — see "call depth guard" below. Otherwise pushes `pc + 1` onto `call_stack`, then jumps to `addr`. Unlike `JUMP`/`JUMP_IF_FALSE`, `addr` is **absolute**, not relative — a class can be called from many different call sites, so a fixed relative offset wouldn't make sense; codegen resolves the true absolute address only after every class's block position is known (see "Multi-class codegen"). |
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
explicitly is display: `utils/runtime.py`'s `display()` helper (shared by
the VM and the interpreter — see "shared runtime helpers" below) checks
`isinstance(value, bool)` *before* any `int` handling and renders
`"true"`/`"false"` instead of Python's `print()` default of
`True`/`False`. `PRINT` (and `print()` in `Interpreter._execute`) always
routes through `display()`.

### shared runtime helpers

`src/utils/runtime.py` holds `display()` and `parse_as()` — logic needed
identically by both the VM and the tree-walking `Interpreter`. Both used
to carry their own private copies of this logic; that duplication was a
real risk (the interpreter and VM could silently diverge on what
`.parse(bool)` accepts, contradicting `docs/architecture.md`'s own claim
that the interpreter is "kept in sync with the VM"), so it's now written
once and imported by both.

### call depth guard

`CALL`/`RETURN` gives classes real recursion (a class can call itself,
directly or through other classes), but nothing in the language stops a
program from recursing forever (`class main() { helper; } class helper()
{ helper; }` compiles and parses fine — there's no static check for this,
matching how a real recursive function call is expected to work). Without
a guard, the VM's `call_stack` (a plain Python list) would simply grow
until the process runs out of memory, and the interpreter's native Python
recursion would eventually raise an uncatchable `RecursionError` that
leaks past `main.py`'s `except EvansLangError` handling as a raw Python
traceback. Both paths cap call depth and raise a clean `EvansLangError`
instead:

- **VM**: `MAX_CALL_DEPTH = 1000` in `src/vm/vm.py`, checked against
  `len(self.call_stack)` before every `CALL`.
- **Interpreter**: `MAX_CALL_DEPTH = 200` in `src/interpreter/interpreter.py`,
  checked against a `self.call_depth` counter (incremented/decremented
  around `_run_class`'s body via `try`/`finally`, so it tracks nesting
  depth, not total call count — many sequential, non-nested calls, e.g.
  from a loop, never approach the limit). This limit is deliberately much
  lower than the VM's: the interpreter costs several native Python stack
  frames per evanslang-level call (`_run_class` → `_execute` → `_run_class`
  → ...), so it has to stay well under Python's own default recursion
  limit (`sys.getrecursionlimit()`, 1000) to actually raise its own error
  first.

Separately, `main`/`init` cannot be called explicitly by name from within
their own file (`_parse_call_statement` in the parser rejects it via
`RESERVED_CLASS_NAMES = {"main", "init"}`) — not because of the recursion
guard, but because both already run automatically, so an explicit local
call would silently run the same body twice in one program execution.
This restriction only applies to the unaliased, local form; calling a
*mentioned* file's `main`/`init` via `alias.main;` is unaffected, since a
mentioned file's `main`/`init` never auto-run in the first place — only
the root file's do.

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

### while/for codegen

Both compile to the same underlying shape — condition check, conditional
skip past the body, then an unconditional jump back to re-check the
condition — reusing the exact same `JUMP_IF_FALSE`/`JUMP` opcodes as `if`,
just with the trailing `JUMP`'s offset made **negative** (the VM's
`pc += instruction.operand` handles negative offsets with no special
casing) so control returns to the top of the loop instead of skipping
forward:

```
condition...
JUMP_IF_FALSE <past body (+ update) + JUMP>
body...
update...                                      (for only)
JUMP <back to condition>
```

`_generate_while` computes the two offsets directly (no multi-branch
patching needed, unlike `if`, since a loop only ever has one body).
`_generate_for` is the same shape with `init` prepended (compiled once,
outside the loop) and `update` appended inside the loop, right before the
jump back — `_generate_statement(node.update)` is reused unchanged, so
`i += 1` in an update clause compiles exactly the same as it would as an
ordinary statement. A `for` with an omitted `<condition>` compiles to
`PUSH_CONST True` in the condition's position (making `JUMP_IF_FALSE`
never fire), which is how `for (;;) {}` becomes an infinite loop rather
than a parse or codegen special case. The interpreter mirrors this with
native Python `while` loops in `_execute` — `WhileStatement` maps directly
to a Python `while`; `ForStatement` runs `node.init` once (if present),
then loops `while node.condition is None or self._evaluate(node.condition)`,
running the body followed by `node.update` (if present) each iteration.

### Multi-class codegen

`CodeGenerator.generate()` works in three passes over `resolved.classes`
(a flat `dict[str, ClassDecl]` keyed by qualified name — `"main"`, or a
path-prefixed key for anything from a mentioned file — already produced,
fully resolved and validated, by the linker):

1. **Compile each class independently.** Every class's body is compiled
   into its own `list[Instruction]` exactly as before (reusing
   `_generate_statement`/`_generate_expression` unchanged), with a
   `RETURN` appended at the end. A `CallStatement` compiles to
   `Instruction(OpCode.CALL, node.resolved_target)` — `resolved_target`
   was already computed by the linker (see `src/linker/`), so codegen
   never re-derives a qualified name from `node.alias`/`node.name` itself;
   it's still a string, not yet an address, since block positions aren't
   known until step 2.
2. **Lay out and record start positions.** A small prologue is prepended:
   `CALL "init"` (only if an `"init"` class exists), then `CALL <entry>`,
   then `HALT`. Every compiled class block is then concatenated after the
   prologue in dict-iteration order, recording `block_starts[name] = <index>`
   as each one is placed.
3. **Patch every CALL.** A final pass walks the fully-assembled
   instruction list and replaces each `CALL`'s string operand with
   `block_starts[target]` — the target's actual absolute position. Since
   the linker already validated every call target (existence and
   `(ment)`-ness) before codegen ever runs, a target missing from
   `block_starts` here means an internal inconsistency, not a user
   mistake — the error message says so rather than guessing at what the
   user did wrong.

Because every class compiles to a self-contained block ending in
`RETURN`, and every call site is a `CALL` to that block's absolute start,
the same class can be called from arbitrarily many places (including
itself, recursively — up to the call depth guard, see above — or two
different classes both calling it) without any code duplication — this is
the payoff of implementing real `CALL`/`RETURN` with a VM call stack
instead of inlining bodies at each call site.
