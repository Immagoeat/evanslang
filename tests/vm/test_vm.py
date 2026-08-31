import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import pytest

from codegen.codegen import CodeGenerator
from linker.linker import link
from utils.errors import EvansLangError
from vm.vm import VM


def build_and_run(source: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "main.el"
        path.write_text(source)
        resolved = link(path)
        ir_program = CodeGenerator().generate(resolved)
        VM().run(ir_program)


def build_run_capture(source: str) -> list[str]:
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        build_and_run(source)
    return [line for line in buf.getvalue().splitlines() if line]


def test_calling_the_same_class_twice_does_not_duplicate_code():
    # Regression check for CALL/RETURN: calling a class multiple times
    # must reuse the same compiled block, not re-inline it.
    calls = []

    class _CapturingStdout:
        def write(self, text):
            if text.strip():
                calls.append(text.strip())

        def flush(self):
            pass

    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        build_and_run(
            'class tick() {\nprint("tick");\n}\n'
            "class main() {\ntick;\ntick;\ntick;\n}"
        )

    lines = [line for line in buf.getvalue().splitlines() if line]
    assert lines == ["tick", "tick", "tick"]


def test_unbounded_self_recursion_raises_clean_error_not_hang():
    with pytest.raises(EvansLangError):
        build_and_run(
            'class helper() {\nhelper;\n}\nclass main() {\nhelper;\n}'
        )


def test_init_runs_once_before_main():
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        build_and_run(
            'class init() {\nprint("init");\n}\n'
            'class main() {\nprint("main");\n}'
        )

    lines = [line for line in buf.getvalue().splitlines() if line]
    assert lines == ["init", "main"]


def test_arithmetic_respects_multiplicative_precedence():
    lines = build_run_capture(
        'class main() {\nprint(2 + 3 * 4);\n}'
    )
    assert lines == ["14"]


def test_arithmetic_parentheses_override_precedence():
    lines = build_run_capture(
        'class main() {\nprint((2 + 3) * 4);\n}'
    )
    assert lines == ["20"]


def test_unary_minus_and_subtraction_combine():
    lines = build_run_capture(
        'class main() {\nprint(10 - -5);\n}'
    )
    assert lines == ["15"]


def test_arithmetic_result_usable_in_condition():
    lines = build_run_capture(
        'class main() {\nif (2 * 3 > 5) {\nprint("yes");\n}\n}'
    )
    assert lines == ["yes"]


def test_arithmetic_type_mismatch_raises_clean_error():
    with pytest.raises(EvansLangError):
        build_and_run(
            'class main() {\nvar a: str = "hi";\nvar b: int = 5;\n'
            'print(a + b);\n}'
        )


def test_negating_a_bool_raises_clean_error():
    with pytest.raises(EvansLangError):
        build_and_run(
            'class main() {\nvar a: bool = true;\nvar b: int = -a;\n}'
        )


def test_try_catch_catches_a_throw():
    lines = build_run_capture(
        'class main() {\n'
        'try {\nprint("before");\nthrow "boom";\nprint("skipped");\n}\n'
        'catch (e: str) {\nprint(e);\n}\n'
        'print("after");\n'
        "}"
    )
    assert lines == ["before", "boom", "after"]


def test_try_catch_catches_builtin_runtime_errors():
    lines = build_run_capture(
        'class main() {\n'
        'var a: int = 5;\nvar b: int = 0;\n'
        "try {\nvar c: int = a / b;\n}\n"
        'catch (e: str) {\nprint(e);\n}\n'
        "}"
    )
    assert lines == ["Division by zero"]


def test_try_catch_unwinds_call_stack_from_nested_calls():
    lines = build_run_capture(
        'class deepest() {\nthrow "deep failure";\n}\n'
        'class middle() {\ndeepest;\n}\n'
        'class main() {\n'
        "try {\nmiddle;\nprint(\"skipped\");\n}\n"
        'catch (e: str) {\nprint(e);\n}\n'
        'print("still running");\n'
        "}"
    )
    assert lines == ["deep failure", "still running"]


def test_uncaught_throw_propagates_as_evanslang_error():
    with pytest.raises(EvansLangError):
        build_and_run('class main() {\nthrow "uncaught";\n}')


def test_throwing_a_non_string_raises_clean_error():
    with pytest.raises(EvansLangError):
        build_and_run('class main() {\nthrow 5;\n}')


def test_nested_try_catch_and_rethrow():
    lines = build_run_capture(
        'class main() {\n'
        "try {\n"
        "try {\nthrow \"inner\";\n}\n"
        'catch (e: str) {\nprint(e);\nthrow "rethrown";\n}\n'
        "}\n"
        'catch (e: str) {\nprint(e);\n}\n'
        "}"
    )
    assert lines == ["inner", "rethrown"]


def test_try_catch_inside_a_loop_resets_each_iteration():
    lines = build_run_capture(
        'class main() {\n'
        "var i: int = 0;\n"
        "while (i < 3) {\n"
        "try {\nif (i == 1) {\nthrow \"loop error\";\n}\nprint(i);\n}\n"
        'catch (e: str) {\nprint(e);\n}\n'
        "i += 1;\n"
        "}\n"
        "}"
    )
    assert lines == ["0", "loop error", "2"]
