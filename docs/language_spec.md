# evanslang language spec

Source files use the `.el` extension.

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
```

Declares a variable named `<NAME>` with the given `<type>` and initializes it
to `<expression>`. The type annotation is mandatory, and the value's type
must match it — a mismatch is a compile-time (parse) error.

```
var EXAMPLE: str = "Hello";
var COUNT: int = 9;
```

## Types

| Type  | Description               | Literal example |
|-------|----------------------------|------------------|
| `str` | Text, double-quoted        | `"Hello"`        |
| `int` | Whole numbers (no sign yet)| `9`               |

## Expressions

Currently supported expressions:
- String literals: `"..."`
- Integer literals: `9`
- Identifiers (referencing a previously declared `var`)

There is no arithmetic, no string concatenation, and no re-assignment of an
existing variable yet.

## Grammar (informal)

```
program     := statement*
statement   := printStmt | varDecl
printStmt   := "print" "(" expression ")" ";"
varDecl     := "var" IDENTIFIER ":" type "=" expression ";"
type        := "int" | "str"
expression  := STRING | INT | IDENTIFIER
```

## Not yet implemented

- Arithmetic and boolean operators
- Re-assignment (`EXAMPLE = "new value";`)
- Control flow (`if`, `while`, `for`)
- Functions
- Comments
