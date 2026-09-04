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


def test_list_index_and_append_match_vm_behavior():
    lines = build_run_capture(
        'class main() {\n'
        "list nums: [1, 2, 3];\n"
        "nums[0] = 9;\n"
        "nums.append(4);\n"
        "print(nums);\n"
        "print(nums.length());\n"
        "}"
    )
    assert lines == ["[9, 2, 3, 4]", "4"]


def test_goto_conditional_loop_matches_vm_behavior():
    source = (
        "class main() {\n"          # line 1
        "var i: int = 0;\n"         # line 2
        "print(i);\n"               # line 3
        "i += 1;\n"                 # line 4
        "if (i < 3) {\n"            # line 5
        "goto ln: 3;\n"             # line 6
        "}\n"                       # line 7
        'print("done");\n'         # line 8
        "}"
    )
    lines = build_run_capture(source)
    assert lines == ["0", "1", "2", "done"]


def test_goto_forward_skips_statements():
    source = (
        "class main() {\n"           # line 1
        'print("start");\n'         # line 2
        "goto ln: 5;\n"              # line 3
        'print("skipped");\n'       # line 4
        'print("landed");\n'        # line 5
        "}"
    )
    lines = build_run_capture(source)
    assert lines == ["start", "landed"]


def test_goto_to_undefined_line_raises_clean_error():
    import pytest

    from utils.errors import EvansLangError

    source = (
        "class main() {\n"
        'print("a");\n'
        "goto ln: 99;\n"
        "}"
    )
    with pytest.raises(EvansLangError):
        build_run_capture(source)
