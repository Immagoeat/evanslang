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
