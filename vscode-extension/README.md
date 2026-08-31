# evanslang VS Code extension

Syntax highlighting and basic autocomplete for `.el` (evanslang) files.

## What's here

- `syntaxes/evanslang.tmLanguage.json` — TextMate grammar: comments, `@mentions`,
  `class`/`main`/`init`/`ment`, `if`/`elseif`/`else`, `while`/`for`, `var`,
  types (`int`/`str`/`float`/`bool`), `true`/`false`, strings, numbers, all
  operators, `.parse(...)`, and class-call identifiers (`NAME;` / `alias.NAME;`).
- `language-configuration.json` — comment toggling (`#`), bracket matching,
  auto-closing pairs for `{}`, `()`, `""`.
- `src/extension.js` — a completion provider offering keywords, types,
  `print`/`input`/`.parse` builtins, and snippets for `class main`,
  `class init`, `class NAME(ment)`, `var`, `if`, `while`, `for`, `@mentions`.

This is intentionally lightweight (grammar + static completions), not a full
language server — there's no live diagnostics, go-to-definition, or
type-aware completion. Given evanslang's current size that tradeoff is
reasonable; revisit if the language keeps growing.

## Installing locally

This extension isn't published to the Marketplace. To install it into your
own VS Code:

```bash
EXT_DIR="$HOME/.vscode/extensions/evanslang-local.evanslang-0.1.0"
mkdir -p "$EXT_DIR"
cp -r vscode-extension/* "$EXT_DIR"/
```

Then reload the window (Command Palette → "Developer: Reload Window", or
just restart VS Code) so it picks up the new extension.

## After changing the grammar or extension.js

Re-run the copy step above, then reload the window again — VS Code doesn't
hot-reload grammars or extension code from a live install.
