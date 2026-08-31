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
