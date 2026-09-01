import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from interpreter.interpreter import Interpreter
from linker.linker import link


def build_run_capture(source: str) -> list[str]:
    import contextlib
    import io

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "main.el"
        path.write_text(source)
        resolved = link(path)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            Interpreter().run(resolved)
    return [line for line in buf.getvalue().splitlines() if line]


def test_writing_through_a_pointer_mutates_the_pointee():
    lines = build_run_capture(
        'class main() {\n'
        "var x: int = 10;\n"
        "var p: ptr<int> = &x;\n"
        "*p = 99;\n"
        "print(x);\n"
        "}"
    )
    assert lines == ["99"]


def test_dereferencing_a_caught_error_variable_works():
    # Regression check: the interpreter's TryStatement handler must box
    # the caught message the same way _store boxes every other variable
    # (it previously wrote a raw str straight into self.variables,
    # crashing the next LOAD/Identifier read with AttributeError).
    lines = build_run_capture(
        'class main() {\n'
        "try {\n"
        'throw "boom";\n'
        "}\n"
        "catch (e: str) {\n"
        "var p: ptr<str> = &e;\n"
        "print(*p);\n"
        "}\n"
        "}"
    )
    assert lines == ["boom"]
