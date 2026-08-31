# evanslang
Evan's coding language

## Quick start

Add `bin/` to your `PATH` (or call `bin/evlng` directly):

```bash
export PATH="$PATH:$(pwd)/bin"
```

Write a program (`.el` file). Every program's body must live inside
`class main() { ... }`:

```
class main() {
    var EXAMPLE: str = "Hello";
    print(EXAMPLE);
}
```

Build and run it:

```bash
evlng --build hello.el hello   # writes hello.evlc
evlng --run hello               # resolves to hello.evlc
```

See `evlng --help` for all options.

## Docs

- [`docs/language_spec.md`](docs/language_spec.md) — language syntax and semantics
- [`docs/architecture.md`](docs/architecture.md) — compiler pipeline and internals
