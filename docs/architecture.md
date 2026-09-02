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
| `src/nodes/` | AST node classes (`Program`, `ClassDecl`, `Mention`, `CallStatement`, `PrintStatement`, `ExpressionStatement`, `VarDecl`, `Assignment`, `DerefAssignment`, `InputCall`, `ParseCall`, `BinaryOp`, `UnaryOp`, `AddressOf`, `Dereference`, `ListLiteral`, `ListDecl`, `IndexExpr`, `IndexAssignment`, `AppendCall`, `LengthCall`, `IfStatement`, `WhileStatement`, `ForStatement`, `TryStatement`, `ThrowStatement`, `StringLiteral`, `IntLiteral`, `FloatLiteral`, `BoolLiteral`, `Identifier`). Named `nodes` rather than `ast` to avoid shadowing Python's stdlib `ast` module. `Program` holds `classes: dict[str, ClassDecl]` (keyed by class name, within one file) and `mentions: list[Mention]` — there is no flat top-level statement list any more; every statement lives inside some `ClassDecl.body`. `ForStatement.init`/`.condition`/`.update` are each `Node | None`, since every clause of a C-style `for(...)` header is individually optional. `TryStatement` holds `try_body`/`catch_var_name`/`catch_body`; `ThrowStatement` holds a single `expression`. `AddressOf` holds a plain variable `name` (not an arbitrary expression — `&` only ever takes the address of a declared variable); `Dereference` holds an `operand` expression (`*p`, or `*(...)` more generally as a read); `DerefAssignment` holds `pointer`/`value` (`*p = value;`, a write — kept as its own node rather than folded into `Assignment`, since its target is an expression to evaluate-then-write-through rather than a bare name). `ListLiteral` holds `elements`/`element_type` (the `[...]` expression itself, only ever synthesized by codegen from a `ListDecl`, never parsed directly — see the parser row); `ListDecl` is `list`/`list<type> NAME: [...];`, its own statement rather than reusing `VarDecl`, holding `name`/`element_type` (`None` for an untyped `list`)/`elements`; `IndexExpr`/`IndexAssignment` are `NAME[index]` as a read vs. `NAME[index] = value;` as a write (mirroring the `Dereference`/`DerefAssignment` split for pointers); `AppendCall`/`LengthCall` are `NAME.append(value)`/`NAME.length()`. `AsciiStatement` holds a single `path` expression (`ascii <expression>;`), mirroring `ThrowStatement`'s shape. `VideoStatement` is identical in shape (`video <expression>;`) — kept as its own node rather than sharing `AsciiStatement` since its codegen and VM/interpreter handling are otherwise entirely separate (a still image vs. a decode-and-play loop). |
| `src/parser/` | Recursive-descent `Parser` that turns one file's tokens into an AST. `parse()` first calls `_prescan_names()` — a single linear pass over the top-level tokens (tracking `{`/`}` depth so it only looks at depth 0) that collects every class name and `@mentions` alias *before* real parsing begins. This is what lets a class body call another class declared later in the same file, or `alias.NAME;` calls resolve against an alias declared anywhere in the file — without it, forward references would fail since a statement is parsed before the parser has seen the later `class` keyword. After the prescan, `parse()` reads `mention*` then `class*` via `_parse_mention`/`_parse_class`; a file needs at least one class or mention to parse, but does *not* need a `class main()` — that check is the linker's job (see below), since a file might only ever be `@mentions`-ed, never run directly. Tracks each variable's declared type in `Parser.declared_types` as it parses `var` statements, and uses that table to type-check both initializers and later `Assignment`s at parse time (a mismatch, or an assignment to an undeclared name, is a `ParseError`). Expression parsing is a standard precedence chain: `_parse_expression` (`\|\|`) → `_parse_and` (`&&`) → `_parse_unary_not` (prefix `!`, recursive so `!!a` works) → `_parse_comparison` (`==`, `!=`, `<`, `<=`, `>`, `>=`, all non-associative — one comparison per expression, no chaining like `a < b < c`) → `_parse_additive` (`+`, `-`, left-associative) → `_parse_multiplicative` (`*`, `/`, left-associative) → `_parse_unary_minus` (prefix `-`/`*`/`&`, recursive for `-`/`*` so `--a`/`**p` work) → `_parse_primary`. `_parse_unary_minus` also handles prefix `*` (dereference, producing `Dereference`) and prefix `&` (address-of, producing `AddressOf`) despite its name, since both bind at the same tight precedence tier as unary `-` and reusing the existing method avoids adding two more near-identical single-purpose methods; a `STAR` token reaching this method is always a prefix dereference, never multiplication, because infix `*` is fully consumed one level up by `_parse_multiplicative`'s own loop before control ever gets here. `_parse_primary` also accepts a parenthesized `"(" expression ")"`, re-entering the chain from the top so parens can wrap anything (including `||`/`&&`). None of the comparison/boolean/arithmetic operators are type-checked at parse time beyond the assigned/initialized variable's declared type (`_check_type` accepts a `BinaryOp`/`UnaryOp` producing a `bool` only for `bool` targets, and one producing `int`/`float` only for `int`/`float` targets, without tracing operand types) — actual operand compatibility for `<`/`<=`/`>`/`>=`/`+`/`-`/`*`/`/`/unary `-` is checked at runtime instead (see Error handling). `_parse_if_statement` parses the `if` branch, then loops on `elseif` and finally an optional `else`, sharing `_parse_block` (`{ statement* }`) across all three; `_skip_optional_semicolon` tolerates (but doesn't require) a `;` after any block. `_parse_while_statement` is a thin wrapper around the same `_parse_block` machinery. `_parse_for_statement` parses `(`, then each of `init`/`condition`/`update` only if the next token isn't the delimiter that would end that clause (`;`, `;`, `)` respectively), so all three are independently optional (`for (;;) {}` parses fine). `init`/`update` reuse `_parse_var_decl`/`_parse_assignment`/`_parse_compound_assignment` with a `consume_semicolon: bool = True` parameter (`False` from the `for` header, since the header's own `;`/`)` delimits the clause instead of the statement's usual trailing `;`) — this is the only reason those three methods take that parameter at all; every other call site uses the default. `_parse_compound_assignment` desugars `NAME += expr;` (and `-=`/`*=`/`/=`) into a plain `Assignment(NAME, BinaryOp(op, Identifier(NAME), expr))` at parse time — the VM/interpreter never see a distinct "compound assignment" concept, only the `Assignment` + `BinaryOp`/`UnaryOp` they already handle. `int` and `float` are enforced as strictly non-interchangeable everywhere a type is checked (`_check_type`, `_parse_compound_assignment`'s `literal_types` map keyed by declared type) — no widening either direction. `_parse_primary` handles `IDENTIFIER "." "parse" "(" type ")"` by requiring `declared_types` confirms the target is a declared `str` (a parse-time error otherwise, since parsing a non-`str` never makes sense), then requiring the parenthesized argument be one of `VALID_TYPES` (`ParseError` on an unknown type name), producing `ParseCall(target, target_type)`; `_check_type` compares `value.target_type` directly against the declared type of whatever the call is assigned/initialized into (exact match required — `var f: float = s.parse(int);` is a `ParseError` even though both sides are numeric, since `ParseCall` now always carries a concrete, known type rather than the pre-`(type)` design where it was accepted for both `int` and `float` because the real type wasn't knowable until runtime). `_parse_statement` distinguishes three different meanings of `IDENTIFIER "."` by checking `mention_aliases`/`class_names` (populated by the prescan) *before* falling back to `.parse`: `alias.NAME;` (alias is a known mention) → `_parse_call_statement`; `str_var.parse(type)` → `_parse_expression_statement` wrapping a `ParseCall`; bare `NAME;` where `NAME` is a known class → also `_parse_call_statement`. `_parse_call_statement` rejects an unaliased call to a name in `RESERVED_CLASS_NAMES = {"main", "init"}` (a `ParseError`, since both already run automatically — see "call depth guard" in the opcode section below); the check only applies to the local, unaliased form, since a *mentioned* file's `main`/`init` never auto-run and so can't double-run from an explicit `alias.main;`/`alias.init;` call. `_parse_try_statement` parses `try` block, then a required `catch (IDENTIFIER: "str")` block (no `finally`, `catch` is mandatory — a `ParseError` if missing); the catch variable's name is registered in `declared_types` as `"str"` before parsing the catch body, the same way `_parse_var_decl` registers a `var`, so the caught value can immediately be used anywhere a declared `str` is expected (e.g. `e.parse(int)`). `_parse_throw_statement` just parses `"throw" expression ";"` into a `ThrowStatement` — `throw`'s expression isn't required to be a `StringLiteral` at parse time (matching the runtime-only checking of arithmetic/comparison operand types elsewhere); a non-`str` throw is instead a runtime error. See "try/catch/throw" below for the full mechanism. Type names are parsed by `_parse_type_name()` (used everywhere `_parse_var_decl` used to inline a bare `_expect(IDENTIFIER)` + `VALID_TYPES` check), which additionally recognizes `"ptr" "<" type ">"` and returns it as a single string (`"ptr<int>"`) rather than restructuring `declared_types`' value type — the pointee must be in `POINTABLE_TYPES` (same as `VALID_TYPES`; no `ptr<ptr<...>>`). `_check_type` has a dedicated `AddressOf` branch: the target type must start with `"ptr<"`, and the addressed variable's own declared type (looked up in `declared_types`) must exactly equal the pointee type, or it's a `ParseError` — a `ptr<...>`-typed target that falls through every branch without matching `AddressOf` hits a catch-all `ParseError` at the end (so `var p: ptr<int> = 5;` is rejected, not silently accepted). `*p = value;` is parsed by `_parse_deref_assignment`, which requires the pointer side to be a bare `IDENTIFIER` (so its declared type — and therefore the pointee type to check `value` against — is known at parse time; `**p = v;`/pointer-to-pointer isn't supported, so this is never a real limitation) and reuses `_check_type` against that pointee type, producing a `DerefAssignment`. `_parse_list_decl` handles `list`/`list<type> NAME: [...];` — an optional `"<" type ">"` (checked against `LIST_ELEMENT_TYPES`, same set as `POINTABLE_TYPES`) sets `element_type`, then `NAME`, then either a bare `;` (sugar for an empty list — unlike `var NAME: type;`, which has no storage until first assigned, `list NAME;` is immediately `.append`-able) or `": " listLiteral`. `self.declared_types[name]` gets `"list"` or `f"list<{element_type}>"` (same string-based scheme as `ptr<type>`); a second dict, `self.list_element_types[name]`, separately tracks just the element type name (`None` for untyped), since `.append(...)`/index-assignment need to look that up on its own to find the right `LITERAL_TYPES_BY_NAME` entry rather than re-parsing the `"list<...>"` string. When `element_type` is set, every element of a literal initializer is checked against it immediately (`ParseError` on a mismatched literal) — the same check runs again in `_parse_index_assignment` and the `.append` branch of `_parse_primary` for their right-hand-side value, but only when that value is itself one of the four literal node types; a non-literal expression (a variable, a `.parse(...)` call, arithmetic, …) can't be type-checked without evaluating it, so it's let through at parse time and checked at runtime instead (see "lists" below) — this mirrors the existing precedent (arithmetic/comparison operand types, `ptr<type>` pointee checks) of "check what's staticly knowable, defer the rest to runtime". `IDENTIFIER "[" ...` is handled in two places: `_parse_statement` routes it to `_parse_index_assignment` when followed by `=` (an assignment), while `_parse_primary` handles a bare `NAME[index]` as a read, producing `IndexExpr`. Both call a shared `_require_list(name_token)` helper that raises `ParseError` unless `declared_types[name]` is `"list"` or starts with `"list<"` — this is what makes indexing/`.append`/`.length` on a non-list variable a parse-time error rather than a confusing runtime one. `.append(...)`/`.length()` are handled inside `_parse_primary`'s existing `IDENTIFIER "." ...` branch, alongside `.parse(...)` — that branch now dispatches on the method name (`"parse"`/`"append"`/`"length"`, `ParseError` on anything else) rather than assuming `.parse` unconditionally the way it used to. `_parse_ascii_statement` just parses `"ascii" expression ";"` into an `AsciiStatement` — the path expression isn't required to be a `StringLiteral` at parse time (same as `throw`, and for the same reason: a `str` variable should work too), so a non-`str` path is a runtime error instead. `_parse_video_statement` is the same shape for `"video" expression ";"` → `VideoStatement`. |
| `src/linker/` | `link(root_path)` resolves `@mentions` and produces a `ResolvedProgram`. Each linked file gets a **scope**: its own resolved (absolute) `Path`, used both as the namespace prefix for its classes (`f"{path}{SEPARATOR}{name}"`, `SEPARATOR = "::"`) and as the key into two shared dicts threaded through the recursion — `classes` (every class from every linked file, keyed by scope) and `ment_by_scope` (`{scope: {class_name: is_ment}}`). The root file is the one exception: its own classes keep bare names (`_qualify` special-cases `scope == root_scope`), so `class main() {}` stays reachable as `"main"`. `_link_file` links a file **once**: it records `ment_by_scope[path]` immediately (before recursing), then processes that file's own `@mentions` (each target gets `_link_file`'d — skipped via `if path in ment_by_scope: return` if some other edge in the graph already linked it), then resolves every `CallStatement` in that file's own class bodies via `_resolve_calls_in_body`, which walks into `if`/`elseif`/`else`/`while`/`for`/`try`/`catch` bodies (via `_statements_in`) to find calls nested arbitrarily deep. A local call (`NAME;`, `node.alias is None`) resolves to `_qualify(scope, ..., name)` — the *current* file's own scope. An aliased call (`alias.NAME;`) looks `node.alias` up in *that file's own* `alias_scopes` dict (built from *that file's own* `@mentions` lines, not the caller's) to find the target file's scope, then checks `ment_by_scope[target_scope][name]` before allowing it — reaching a non-`ment` class via an alias is an `EvansLangError` right here, at link time, not deferred to codegen. Each `CallStatement.resolved_target` is set to the final qualified string; codegen/interpreter read it directly rather than re-deriving it (previously both had their own copy of the qualification logic, which produced the wrong scope whenever a call reached into a file linked in under a different path than the literal alias text implied — this per-file alias scoping is what makes `docs/language_spec.md`'s "`@mentions` only sees classes declared directly in the file it names" hold even when a mentioned file's own class bodies use *that file's own* `@mentions`). Two `@mentions` lines in the same file reusing one alias for two different files is a link-time error (`alias_scopes` rejects the second one). `link()` raises if the *root* file's class set has no `"main"` — mentioned-only library files are exempt, since `Parser.parse()` never required it of them. |
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
| `STORE <name>` | Pop the stack; if `name` has no `Cell` yet, create one holding the value, otherwise reuse the existing `Cell` and overwrite its `.value` (so a pointer taken via `ADDR_OF` before this `STORE` still observes the new value afterward — see "pointers" below). |
| `LOAD <name>` | Push `variables[name].value` (error if `name` is undefined). |
| `ADDR_OF <name>` | Push `variables[name]` itself — the `Cell` object, not its value — as a first-class pointer (error if `name` is undefined). See "pointers" below. |
| `DEREF` | Pop a value; if it isn't a `Cell`, raises `EvansLangError`. Otherwise push `cell.value`. |
| `DEREF_STORE` | Pop `value`, then pop `cell` (in that order — the pointer expression is evaluated first by codegen, so it's deeper on the stack); if `cell` isn't a `Cell`, raises `EvansLangError`. Otherwise set `cell.value = value`. |
| `INPUT` | Pop a prompt string, call `input(prompt)`, push the result. |
| `PARSE <target_type>` | Pop a string, convert it to `target_type` (`"int"`, `"float"`, `"bool"`, or `"str"`) via `utils.runtime.parse_as` — `str` is the identity; `bool` accepts exactly `"true"`/`"false"`; `int`/`float` use normal numeric parsing. Raises `EvansLangError` if the string doesn't match `target_type`. Push the result. |
| `POP` | Pop and discard the top of the stack. Emitted for `ExpressionStatement` (e.g. a bare `bob.parse(int);`) so the produced value doesn't linger on the stack. |
| `PRINT` | Pop the stack and print it. |
| `EQ` / `NEQ` | Pop two values, push `left == right` / `left != right`. No type-checking — comparing an `int` to a `str` is allowed. |
| `LT` / `LTE` / `GT` / `GTE` | Pop two values, push `left <op> right` using Python's native ordering comparison. Raises `EvansLangError` if the operand types aren't comparable (e.g. `int` vs `str`), via `VM._compare()`. |
| `AND` / `OR` | Pop two values, push `bool(left) and bool(right)` / `bool(left) or bool(right)`. Both operands are always evaluated by codegen before the opcode runs — no short-circuiting. |
| `NOT` | Pop one value, push `not value`. |
| `NEG` | Pop one value, push `-value`. Raises `EvansLangError` if the value isn't `int`/`float`, or is a `bool` (checked explicitly, since Python's `bool` is an `int` subclass and would otherwise silently negate `true`/`false`). |
| `ADD` / `SUB` / `MUL` / `DIV` | Pop `right` then `left`, push `left <op> right` via `VM._arithmetic()`. `DIV` checks the runtime Python types of both operands: floor division (`//`) if both are `int`, real division (`/`) otherwise (i.e. either operand is a `float`); raises `EvansLangError` on division by zero either way. `_arithmetic()` wraps the operation in `try/except TypeError`, re-raising as `EvansLangError` (e.g. `"a" + 5`) rather than letting a raw Python `TypeError` escape — mirrors `_compare()`'s existing pattern for `<`/`<=`/`>`/`>=`, and matters because `try`/`catch` needs a single error type to catch. |
| `JUMP_IF_FALSE <offset>` | Pop a value; if falsy, add `offset` to the program counter (`offset` is relative to this instruction's own index, so `+1` means "the next instruction"). |
| `JUMP <offset>` | Unconditionally add `offset` to the program counter. Emitted at the end of each `if`/`elseif` branch body to skip past the remaining branches and any `else` once a branch has run. |
| `CALL <addr>` | If `call_stack` is already `MAX_CALL_DEPTH` (1000) deep, raises `EvansLangError` rather than recursing further — see "call depth guard" below. Otherwise pushes `pc + 1` onto `call_stack`, then jumps to `addr`. Unlike `JUMP`/`JUMP_IF_FALSE`, `addr` is **absolute**, not relative — a class can be called from many different call sites, so a fixed relative offset wouldn't make sense; codegen resolves the true absolute address only after every class's block position is known (see "Multi-class codegen"). |
| `RETURN` | Pop an address off `call_stack` and jump there. Raises `EvansLangError` ("Return with no active call") if the call stack is empty — not reachable through normal codegen output, since every compiled class body ends in exactly one `RETURN` matching the `CALL` that invoked it. |
| `TRY_BEGIN <offset>` | Push `(pc + offset, len(stack), len(call_stack))` onto `VM.handler_stack` — `pc + offset` is the catch block's start (relative, same convention as `JUMP`), and the recorded stack/call_stack lengths are what an unwind truncates back to. See "try/catch/throw" below. |
| `TRY_END` | Pop the top of `handler_stack` — the try body completed without an error, so its handler is no longer active. |
| `THROW` | Pop a value; if it isn't a `str`, raises `EvansLangError` (a non-`str` throw is itself a caught-able runtime error). Otherwise raises `EvansLangError(value)`, which unwinds through `VM.run()`'s dispatch loop exactly like any other runtime error. |
| `LIST_NEW <(count, element_type)>` | Pop `count` values off the stack (in the order they were pushed — codegen emits each element left-to-right before this instruction), push a new `EvList` (see "lists" below) tagged with `element_type` (`None` for an untyped list). |
| `INDEX_GET` | Pop `index`, then `target`; push `target[index]` via `VM._index()`, which raises `EvansLangError` if `target` isn't a `list`, `index` isn't a non-`bool` `int`, or `index` is out of range. |
| `INDEX_SET` | Pop `value`, then `index`, then `target` (value evaluated last by codegen, so it's shallowest); runs the same element-type check as `LIST_APPEND` below, then writes `target[index] = value` via `VM._index_set()` (same bounds/type checks as `INDEX_GET`). |
| `LIST_APPEND` | Pop `value`, then `target`; raises `EvansLangError` if `target` isn't a `list`. Checks `value` against `target`'s tagged `element_type` (if any) via `utils.runtime.check_element_type` — a mismatch is `EvansLangError`, not a silent type violation. Appends, then pushes `value` back (so `.append(...)` has something to give an `ExpressionStatement`'s trailing `POP`, and so `.append(...)` is itself usable as an expression, not only a bare statement). |
| `LIST_LEN` | Pop `target`; raises `EvansLangError` if it isn't a `list`. Push `len(target)`. |
| `ASCII` | Pop `path`; raises `EvansLangError` if it isn't a `str`. Otherwise calls `utils.runtime.render_ascii_art(path)` and prints the result. Pushes nothing — `AsciiStatement` codegen doesn't emit a trailing `POP` the way `ExpressionStatement` does, since `ascii ...;` is a statement in its own right, not an expression wrapped in one (unlike `.append(...)`, which pushes its value back precisely so it works as either). See "ascii" below. |
| `VIDEO` | Pop `path`; raises `EvansLangError` if it isn't a `str`. Otherwise calls `utils.runtime.play_ascii_video(path)`, which blocks until every frame has played. Pushes nothing, for the same reason as `ASCII`. See "video" below. |
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

`src/utils/runtime.py` holds `display()`, `parse_as()`, `Cell`, `EvList`,
`check_element_type()`, `render_ascii_art()`, and `play_ascii_video()` —
logic and state needed identically by both the VM and the tree-walking
`Interpreter`. Both used to carry their own
private copies of this logic; that duplication was a real risk (the
interpreter and VM could silently diverge on what `.parse(bool)` accepts,
contradicting `docs/architecture.md`'s own claim that the interpreter is
"kept in sync with the VM"), so it's now written once and imported by
both. `Cell` started as VM-only (added for pointers) but moved here once
the interpreter needed the exact same boxing — and once `display()`
needed to recognize a bare `Cell` value (from `print(<pointer>)`, not
`print(*<pointer>)`) and render it as `f"ptr@{id(value):x}"` rather than
leaking Python's own `<...Cell object at 0x...>` repr; putting `Cell` in
`vm.py` while `display()` lived in `runtime.py` would have made
`runtime.py` import from `vm.py` while `vm.py` already imports `display`
from `runtime.py` — a cycle, avoided by giving `Cell` the same shared home
as the rest of this module. `EvList`/`check_element_type()` are here for
the identical reason — see "lists" below. `display()` also now recognizes
a bare `list` (which `EvList` is a subclass of, so `isinstance(value,
list)` catches it) and formats each element recursively, quoting `str`
elements (`["a", 1, true]`) so a list of strings doesn't look
indistinguishable from a list of bare words in the printed output.

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

### try/catch/throw

**Codegen** (`CodeGenerator._generate_try`) lays out a `TryStatement` as:

```
TRY_BEGIN <past try body + TRY_END + JUMP, to catch>
<try body...>
TRY_END
JUMP <past catch body>
STORE <catch_var>
<catch body...>
```

`TRY_BEGIN`'s operand is computed the same way as `if`/`while`'s jump
offsets — relative to its own instruction, pointing past the try body,
`TRY_END`, and the trailing `JUMP` to the `STORE` that starts the catch
block. The `STORE` is what actually binds the caught value: the VM pushes
the error's message onto the stack before jumping there (see below), so
the catch block's first instruction always consumes it, the same way
`VarDecl`/`Assignment` codegen already ends in a `STORE`. `ThrowStatement`
compiles to `<expression...>, THROW`.

**VM** (`vm/vm.py`) tracks an explicit `handler_stack` of
`(catch_pc, stack_depth, call_depth)` tuples, parallel to `call_stack` —
the same "explicit stack alongside the flat instruction array" approach
`CALL`/`RETURN` already uses, rather than mapping VM-level control flow
onto Python's own `try`/`except` (which would require the VM to recurse in
Python for every evanslang `try`, unlike everything else it does).
`VM.run()`'s dispatch loop wraps each instruction's execution in
`try/except EvansLangError`: `TRY_BEGIN` pushes a handler recording where
to jump and the stack/call_stack lengths to restore; `TRY_END` pops it
once the try body finishes cleanly. If any instruction — including deep
inside a chain of `CALL`s, since `EvansLangError` propagates up through
however many nested Python calls `VM.run()`/`_dispatch()` are on the
call stack, independent of the *evanslang*-level `call_stack` — raises
`EvansLangError` while a handler is active, `run()` catches it, pops the
handler, truncates `self.stack`/`self.call_stack` back to the recorded
lengths (unwinding out of however many evanslang-level calls were
in progress), pushes `error.message`, and resumes at `catch_pc`. With no
active handler, the error re-raises and propagates to the CLI exactly like
any other runtime error. Because this reuses the single existing
`EvansLangError` type — the same one `_compare()`/`_arithmetic()`/`NEG`/
`LOAD`/`CALL`/`RETURN` already raise for their own runtime errors — a
`catch` block catches explicit `throw`s and built-in runtime errors
uniformly, with no separate error hierarchy needed.

**Interpreter** (`interpreter.py`) doesn't need any of this machinery: a
`TryStatement` is executed as a native Python `try/except EvansLangError`
around the try body, binding `error.message` under `catch_var_name` via
`self._store()` (see "pointers" below — every variable write goes through
`_store`, not a direct `self.variables[...] = ...`, so the caught value is
boxed the same way any other variable is) before running the catch body —
Python's own exception propagation already unwinds through nested
`_run_class`/`_execute` calls (and their `call_depth`-decrementing
`finally` blocks) exactly the way the VM's handler-stack unwind does by
hand. `ThrowStatement` evaluates its expression, checks it's a `str`, and
raises `EvansLangError` directly.

### pointers

`&x` (address-of) and `*p` (dereference)/`*p = v;` (deref-assignment) need
every variable's storage to be a mutable *slot* that multiple names can
share a reference to, not a plain value in a flat dict — otherwise
`self.variables["x"] = 5` has no way to also be visible through some other
name `p` that points at `x`. Both the VM and interpreter box every
variable in a `Cell` (`utils/runtime.py`, see "shared runtime helpers"
above): `variables[name]` is always a `Cell`, and `Cell.value` is the
actual evanslang value. `&x` becomes "push/return the `Cell` object
itself" (`ADDR_OF` in the VM, `AddressOf` handling in the interpreter's
`_evaluate`) — the pointer's *runtime value* is the `Cell`, not a copy of
anything. `*p` reads `cell.value`; `*p = v;` writes `cell.value = v`.

**Reassignment reuses the Cell.** A `var`/plain `Assignment` (VM's
`STORE`, interpreter's `_store()` helper) does *not* replace
`variables[name]` with a fresh `Cell` on every write — it reuses the
existing one if `name` already has a `Cell`, only overwriting `.value`.
This is what makes `var p: ptr<int> = &x; x = 20; print(*p);` print `20`:
if `STORE`/`_store` instead did `variables[name] = Cell(value)` every
time, `x`'s later assignment would silently detach it from whatever `p`
captured earlier, and pointers would only ever see the value at the
moment `&x` ran. A pointer *variable* itself (`p`) is freely reassignable
the same way (`p = &y;` just overwrites `p`'s own `Cell.value` with a
different `Cell` reference — `p`'s `Cell` and the `Cell` it points to are
two separate boxes).

**Type checking is entirely parse-time, except operand compatibility.**
`_parse_type_name()` parses `ptr<type>` and stores it as one string
(`"ptr<int>"`) in `declared_types`; `_check_type` requires the value being
assigned to a `ptr<...>`-typed target to be an `AddressOf` whose addressed
variable's own declared type exactly matches the pointee (see the parser
row in Modules above). Because the pointer's target variable is a plain
`IDENTIFIER` in `_parse_deref_assignment` (not an arbitrary expression),
its declared type — and therefore the pointee type to type-check the
right-hand side against — is always known at parse time, the same way a
plain `Assignment`'s target type is; there's no runtime type-tag on a
`Cell` itself; a `Cell` can in principle hold any evanslang value, and
nothing stops two differently-`ptr<type>`-typed pointers at runtime from
both resolving to the same underlying `Cell` if the parser's checks were
somehow bypassed — but the parser is the only path to constructing an
`AddressOf`/`DerefAssignment`, so this is enforced, not just assumed.
`DEREF`/`DEREF_STORE` (and the interpreter's matching checks) still verify
at runtime that the value being dereferenced actually is a `Cell` — not a
type match on the pointee, just a "this is a pointer at all" guard, the
same spirit as `NEG` checking its operand is numeric.

**Printing a raw pointer** (`print(p)`, not `print(*p)`) goes through
`display()`, which recognizes a bare `Cell` and renders
`f"ptr@{id(value):x}"` — an opaque, address-shaped marker — rather than
either crashing or (worse) silently printing the pointee's value, which
would make `print(p)` and `print(*p)` indistinguishable in output.

### lists

A list's runtime value is a plain Python `list` — specifically
`utils.runtime.EvList`, a thin `list` subclass carrying one extra
attribute, `element_type` (`str | None`), the declared pointee type for a
`list<type>` (`None` for an untyped `list`). It's stored inside a `Cell`
exactly like every other variable's value (see "pointers" above and
`STORE`'s row in the opcode table) — lists needed no new storage concept
at all, only new opcodes to build/read/mutate the Python list a `Cell` now
sometimes holds. Subclassing `list` (rather than wrapping one, the way
`Cell` wraps an arbitrary value) means every existing `isinstance(value,
list)` check — `display()`'s list-formatting branch, `VM._index()`'s
"is this actually a list" guard, `.append`/`.length`'s guards — keeps
working unchanged; `element_type` just rides along as extra metadata.

**Building a list literal.** `ListLiteral`/`ListDecl` codegen emits each
element expression left-to-right, then a single `LIST_NEW <(count,
element_type)>` that pops exactly `count` values off the stack (codegen
already knows how many elements it emitted, so no runtime length-sniffing
is needed) and wraps them in a fresh `EvList` tagged with `element_type`.
This is the only place an `EvList` is ever constructed — `.append(...)`
mutates an existing one in place rather than building a new tagged list,
so the tag set at construction time persists for the list's whole
lifetime, the same way a `ptr<type>`'s pointee type is fixed at the
`&x` that created it.

**Type checking has two layers, at two different times**, mirroring how
`ptr<type>`/arithmetic operand checks already split between parse time and
runtime:
1. **Parse time, literals only.** `_parse_list_decl` checks every element
   of a `list<type>` initializer that's a literal node (`IntLiteral`,
   `StringLiteral`, `FloatLiteral`, `BoolLiteral`) against `element_type`
   directly (`ParseError` on a mismatch); `_parse_index_assignment` and
   the `.append` branch of `_parse_primary` do the same for their
   right-hand-side value. This is necessarily incomplete — a non-literal
   expression (an identifier, arithmetic, a `.parse(...)` call, …) can't
   be type-checked without evaluating it, so the parser lets it through.
2. **Runtime, everything.** `utils.runtime.check_element_type(target,
   value, action)` is the second layer: given any runtime `target` (an
   `EvList` or otherwise) and a `value` about to be appended/assigned in,
   it looks up `target.element_type` and — if set — checks `value`'s
   Python type against it via `ELEMENT_TYPE_CHECK` (a small dict of
   per-type predicates, `bool` checked *before* `int` since Python's
   `bool` is an `int` subclass), raising `EvansLangError` on a mismatch.
   Called from both `VM`'s `INDEX_SET`/`LIST_APPEND` opcode handlers and
   the interpreter's matching `IndexAssignment`/`AppendCall` evaluation —
   written once in `utils/runtime.py` for the same reason `display()`/
   `parse_as()` are (see "shared runtime helpers" above), so the VM and
   interpreter can't silently diverge on what a `list<int>` actually
   rejects. This is what catches `nums.append(some_str_variable)` against
   a `list<int>` — a case parse-time literal-checking alone can't see
   through, since `some_str_variable` isn't a literal node at all.

**Indexing** (`INDEX_GET`/`INDEX_SET`, and the interpreter's matching
`_index()`/`_index_set()` methods — identical logic, kept in both VM and
`Interpreter` classes the same way `_compare()`/`_arithmetic()` are, since
there's no shared "helper that needs an active call stack or VM instance"
place to put them in `utils/runtime.py`) requires the index to be a
non-`bool` `int` and in range (`0 <= index < len(target)`), raising a
descriptive `EvansLangError` (naming the actual index and the list's
current length) otherwise — deliberately not Python's own `IndexError`,
since that would escape evanslang's error-handling entirely and couldn't
be `catch`able.

**`.append(...)` returns the appended value** (both the `LIST_APPEND`
opcode and the interpreter's `AppendCall` evaluation push/return `value`,
not `None`/nothing) so that `.append(...)` is usable in two different
statement forms without special-casing either: as a bare
`ExpressionStatement` (`nums.append(1);`, where the codegen-emitted
trailing `POP` needs *something* on the stack to discard) and, in
principle, as a sub-expression elsewhere (`print(nums.append(1));` prints
the value just appended) — nothing in the grammar currently requires the
second form, but it falls out for free rather than needing a special
"statement-only" restriction.

### ascii

`ascii <expression>;` is evanslang's first feature that touches the
filesystem or a third-party library — everything before it (the compiler,
the VM, the interpreter) runs on nothing but the Python standard library.
The actual image decoding and downscaling is delegated entirely to
[Pillow](https://pillow.readthedocs.io/) (`pillow` in `requirements.txt`);
`utils.runtime.render_ascii_art(path)` is a thin wrapper around it, shared
by the VM's `ASCII` opcode handler and the interpreter's `AsciiStatement`
execution (same "write once in `utils/runtime.py`" reasoning as
`display()`/`parse_as()`/`Cell` — see "shared runtime helpers" above).

**The Pillow import is lazy** — `from PIL import Image` happens inside
`render_ascii_art()`, not at module load time, so importing
`utils/runtime.py` (and therefore every module that transitively imports
it: the VM, the interpreter, `main.py`) never requires Pillow to be
installed. Only a program that actually executes an `ascii` statement
needs it; if it isn't installed, that's when the `ImportError` gets
caught and re-raised as a normal `EvansLangError` — the same
runtime-error, catchable-with-`try` treatment as a missing image file or
a non-`str` path, rather than a hard crash or an import-time failure that
would break *every* evanslang program regardless of whether they use
`ascii` at all.

**Conversion pipeline**: `Image.open(path)` (wrapped in `try/except`
covering both `FileNotFoundError` specifically and a catch-all `Exception`
for anything else Pillow might raise on a corrupt/unsupported file, each
re-raised as a descriptive `EvansLangError`) → `.convert("L")` to
grayscale (one 0-255 brightness byte per pixel, discarding color, since
the output is single-channel ASCII characters) → `.resize(...)` down to
`_ascii_dimensions(width, height)` — a small shared helper that returns
`(ASCII_WIDTH, height)` scaled by `ASCII_HEIGHT_RATIO` (0.55): this
correction exists because a terminal character cell is taller than it is
wide, so scaling both dimensions by the same factor would visibly stretch
the output vertically; halving-ish the height compensates for that ratio
→ `.tobytes()` to get the resulting grayscale bytes in row-major order
(one byte per pixel, matching `new_width * new_height`) → `_pixels_to_ascii(pixels,
width)`, another shared helper, maps each byte through `ASCII_RAMP`
(`"@%#*+=-:. "`, darkest to lightest, 10 characters) via
`ramp[len(ramp) - 1 - (pixel * (len(ramp) - 1) // 255)]` — darker pixels
(lower brightness byte) map to denser/darker-looking characters (`@`) and
lighter pixels map toward the empty-looking end (`.`/space), matching how
ASCII art conventionally uses character density to stand in for grayscale
brightness — and joins the rows with `\n` into one string, which both the
VM and interpreter just `print()` directly (not through `display()` — the
string is already fully formatted; `display()` is for turning an
arbitrary evanslang *value* into printable text, and this is already
text). `_ascii_dimensions()`/`_pixels_to_ascii()` are both private to
`utils/runtime.py` (not part of its public surface `vm.py`/`interpreter.py`
import) and exist specifically so `render_ascii_art()` and
`play_ascii_video()` (see "video" below) share the exact same
downscaling/ramp-mapping logic — a still image and a video frame are
converted identically, just from different sources.

### video

`video <expression>;` reuses `ascii`'s conversion math but swaps the
source: instead of one Pillow `Image.open()`, it's OpenCV's
`cv2.VideoCapture(path)` read in a loop, one frame at a time, until the
video is exhausted. `play_ascii_video()` (`utils/runtime.py`) is the
shared implementation, called identically from the VM's `VIDEO` opcode
handler and the interpreter's `VideoStatement` execution — same "write
once, both backends stay in sync" reasoning as everything else in this
module.

**Opening and pacing**: `cv2.VideoCapture(path)` never raises on a bad
path the way `PIL.Image.open()` does — a missing or unreadable file just
produces a capture object where `.isOpened()` is `False`, so that's
checked explicitly and turned into an `EvansLangError` (the capture is
still `.release()`d in that case, since OpenCV holds the file open even
for a failed capture). `cap.get(cv2.CAP_PROP_FPS)` reads the source
video's own frame rate; some containers/codecs report `0` (or `nan`) for
this, so a falsy/non-positive value falls back to a hardcoded 24fps
default rather than computing a zero or negative `time.sleep()` duration.

**Per-frame loop**: `capture.read()` returns `(ok, frame)` where `frame`
is a NumPy array in OpenCV's native `BGR` pixel order (not `RGB`,
notably) and `ok` is `False` once the video is exhausted — that's the
loop's exit condition, not a fixed frame count, so it plays exactly as
many frames as the file actually has. Each frame is converted with
`cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)` (analogous to Pillow's
`.convert("L")`) then `cv2.resize(...)` to the same `_ascii_dimensions()`
result `ascii` would use for a same-sized image, then `.tobytes()` and
`_pixels_to_ascii()` — identical downstream conversion to a still image,
just sourced from a video frame's array instead of a `PIL.Image`. Before
printing, `ANSI_CLEAR_SCREEN` (`"\033[2J\033[H"`, clear-screen + cursor-
to-top) is prepended, so each frame overwrites the previous one in the
terminal instead of scrolling — `print(ANSI_CLEAR_SCREEN + ascii_frame)`
in one call, so the clear and the frame reach the terminal together
rather than as two separate writes that could interleave with anything
else touching stdout. `time.sleep(frame_delay)` after each frame is what
paces playback to roughly the source's own frame rate; the whole loop
runs inside a `try/finally` so `capture.release()` always happens, even
if a frame's conversion somehow raised.

**Blocking, not asynchronous**: `video <expression>;` behaves like any
other statement — the VM/interpreter's normal instruction dispatch is
what's driving the per-frame loop and its `time.sleep()` calls, so
nothing else in the program runs until every frame has played and the
statement returns control. There's no way (yet — see "Not yet
implemented" in `docs/language_spec.md`) to play a video in the
background or interrupt it early.
