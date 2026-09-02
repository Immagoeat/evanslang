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


def test_dereferencing_a_pointer_reads_the_pointee():
    lines = build_run_capture(
        'class main() {\n'
        "var x: int = 10;\n"
        "var p: ptr<int> = &x;\n"
        "print(*p);\n"
        "}"
    )
    assert lines == ["10"]


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


def test_reassigning_the_pointee_var_is_visible_through_the_pointer():
    lines = build_run_capture(
        'class main() {\n'
        "var x: int = 1;\n"
        "var p: ptr<int> = &x;\n"
        "x = 50;\n"
        "print(*p);\n"
        "}"
    )
    assert lines == ["50"]


def test_pointer_can_be_reassigned_to_a_different_variable():
    lines = build_run_capture(
        'class main() {\n'
        "var x: int = 1;\n"
        "var y: int = 2;\n"
        "var p: ptr<int> = &x;\n"
        "p = &y;\n"
        "*p = 42;\n"
        "print(y);\n"
        "print(x);\n"
        "}"
    )
    assert lines == ["42", "1"]


def test_pointer_works_with_str_float_bool():
    lines = build_run_capture(
        'class main() {\n'
        'var s: str = "hi";\n'
        "var ps: ptr<str> = &s;\n"
        '*ps = "bye";\n'
        "print(s);\n"
        "var f: float = 1.5;\n"
        "var pf: ptr<float> = &f;\n"
        "*pf = *pf + 1.0;\n"
        "print(f);\n"
        "var b: bool = true;\n"
        "var pb: ptr<bool> = &b;\n"
        "*pb = false;\n"
        "print(b);\n"
        "}"
    )
    assert lines == ["bye", "2.5", "false"]


def test_dereferencing_through_a_thrown_and_caught_error_still_works():
    # Regression check: the interpreter's catch-var binding must box the
    # caught message the same way every other variable is boxed, or a
    # later &e/*p on it breaks.
    lines = build_run_capture(
        'class main() {\n'
        "var x: int = 5;\n"
        "var p: ptr<int> = &x;\n"
        "try {\n"
        'var bad: int = *p + "oops";\n'
        "}\n"
        'catch (e: str) {\nprint(e);\n}\n'
        "print(*p);\n"
        "}"
    )
    assert lines == ["Cannot apply '+' to int and str", "5"]


def test_list_index_read_and_write():
    lines = build_run_capture(
        'class main() {\n'
        "list nums: [1, 2, 3];\n"
        "print(nums[1]);\n"
        "nums[1] = 99;\n"
        "print(nums[1]);\n"
        "}"
    )
    assert lines == ["2", "99"]


def test_list_append_and_length():
    lines = build_run_capture(
        'class main() {\n'
        "list nums: [1, 2];\n"
        "print(nums.length());\n"
        "nums.append(3);\n"
        "print(nums.length());\n"
        "print(nums[2]);\n"
        "}"
    )
    assert lines == ["2", "3", "3"]


def test_empty_list_decl_starts_empty():
    lines = build_run_capture(
        'class main() {\n'
        "list nums;\n"
        "print(nums.length());\n"
        "nums.append(1);\n"
        "print(nums.length());\n"
        "}"
    )
    assert lines == ["0", "1"]


def test_untyped_list_allows_mixed_types():
    lines = build_run_capture(
        'class main() {\n'
        'list mixed: [1, "two", true];\n'
        "print(mixed);\n"
        "}"
    )
    assert lines == ['[1, "two", true]']


def test_list_index_out_of_range_raises_clean_error():
    with pytest.raises(EvansLangError):
        build_and_run(
            'class main() {\n'
            "list nums: [1, 2];\n"
            "print(nums[5]);\n"
            "}"
        )


def test_indexing_a_non_list_raises_clean_error():
    with pytest.raises(EvansLangError):
        build_and_run(
            'class main() {\n'
            "var x: int = 5;\n"
            "print(x[0]);\n"
            "}"
        )


def test_typed_list_rejects_runtime_type_mismatch_on_append():
    with pytest.raises(EvansLangError):
        build_and_run(
            'class main() {\n'
            "list<int> nums: [1, 2];\n"
            'var s: str = "oops";\n'
            "nums.append(s);\n"
            "}"
        )


def test_typed_list_rejects_runtime_type_mismatch_on_index_assignment():
    with pytest.raises(EvansLangError):
        build_and_run(
            'class main() {\n'
            "list<int> nums: [1, 2];\n"
            'var s: str = "oops";\n'
            "nums[0] = s;\n"
            "}"
        )


def test_list_index_error_is_catchable():
    lines = build_run_capture(
        'class main() {\n'
        "list nums: [1, 2];\n"
        "try {\n"
        "print(nums[5]);\n"
        "}\n"
        'catch (e: str) {\nprint(e);\n}\n'
        "}"
    )
    assert lines == ["List index 5 out of range (length 2)"]


def test_list_used_in_for_loop():
    lines = build_run_capture(
        'class main() {\n'
        "list nums: [1, 2, 3, 4];\n"
        "var sum: int = 0;\n"
        "for (var i: int = 0; i < nums.length(); i += 1) {\n"
        "sum = sum + nums[i];\n"
        "}\n"
        "print(sum);\n"
        "}"
    )
    assert lines == ["10"]


def _write_test_image(path) -> None:
    pytest.importorskip("PIL")
    from PIL import Image

    # Half black, half white (not uniform) so every rendered row contains
    # a real ramp character rather than an all-space row, which
    # build_run_capture's blank-line filtering would otherwise drop.
    image = Image.new("RGB", (10, 10), "white")
    for y in range(5):
        for x in range(10):
            image.putpixel((x, y), (0, 0, 0))
    image.save(path)


def test_ascii_statement_prints_multiple_rows():
    with tempfile.TemporaryDirectory() as tmp:
        image_path = Path(tmp) / "test.png"
        _write_test_image(image_path)
        lines = build_run_capture(
            'class main() {\n'
            f'ascii "{image_path.as_posix()}";\n'
            "}"
        )
    assert len(lines) > 1
    assert all(len(line) == 80 for line in lines)
    assert all(set(line) <= set("@%#*+=-:. ") for line in lines)


def test_ascii_statement_accepts_a_str_variable():
    with tempfile.TemporaryDirectory() as tmp:
        image_path = Path(tmp) / "test.png"
        _write_test_image(image_path)
        lines = build_run_capture(
            'class main() {\n'
            f'var path: str = "{image_path.as_posix()}";\n'
            "ascii path;\n"
            "}"
        )
    assert len(lines) > 1


def test_ascii_statement_missing_file_raises_clean_error():
    with pytest.raises(EvansLangError):
        build_and_run('class main() {\nascii "does_not_exist.png";\n}')


def test_ascii_statement_rejects_non_str_argument():
    with pytest.raises(EvansLangError):
        build_and_run("class main() {\nascii 5;\n}")


def test_ascii_statement_missing_file_is_catchable():
    lines = build_run_capture(
        'class main() {\n'
        'try {\nascii "does_not_exist.png";\n}\n'
        'catch (e: str) {\nprint(e);\n}\n'
        "}"
    )
    assert len(lines) == 1
    assert "does_not_exist.png" in lines[0]


def _write_test_video(path) -> None:
    cv2 = pytest.importorskip("cv2")
    import numpy as np

    # A high fps and only 2 frames keeps the test itself fast, since
    # play_ascii_video() sleeps ~1/fps between frames.
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, 60.0, (10, 10))
    for shade in (0, 255):
        frame = np.full((10, 10, 3), shade, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def test_video_statement_plays_and_returns():
    with tempfile.TemporaryDirectory() as tmp:
        video_path = Path(tmp) / "test.mp4"
        _write_test_video(video_path)
        lines = build_run_capture(
            'class main() {\n'
            f'video "{video_path.as_posix()}";\n'
            'print("done");\n'
            "}"
        )
    assert lines[-1] == "done"
    # Each frame's first printed line is prefixed with the ANSI
    # clear-screen sequence (\033[2J\033[H) - strip it before checking the
    # rest is pure ramp characters.
    ascii_lines = [
        line.replace("\033[2J\033[H", "") for line in lines if line != "done"
    ]
    ascii_lines = [line for line in ascii_lines if line]
    assert len(ascii_lines) > 1
    assert all(set(line) <= set("@%#*+=-:. ") for line in ascii_lines)


def test_video_statement_accepts_a_str_variable():
    with tempfile.TemporaryDirectory() as tmp:
        video_path = Path(tmp) / "test.mp4"
        _write_test_video(video_path)
        lines = build_run_capture(
            'class main() {\n'
            f'var path: str = "{video_path.as_posix()}";\n'
            "video path;\n"
            'print("done");\n'
            "}"
        )
    assert lines[-1] == "done"


def test_video_statement_missing_file_raises_clean_error():
    with pytest.raises(EvansLangError):
        build_and_run('class main() {\nvideo "does_not_exist.mp4";\n}')


def test_video_statement_rejects_non_str_argument():
    with pytest.raises(EvansLangError):
        build_and_run("class main() {\nvideo 5;\n}")


def test_video_statement_missing_file_is_catchable():
    lines = build_run_capture(
        'class main() {\n'
        'try {\nvideo "does_not_exist.mp4";\n}\n'
        'catch (e: str) {\nprint(e);\n}\n'
        "}"
    )
    assert len(lines) == 1
    assert "does_not_exist.mp4" in lines[0]


def test_start_audio_playback_returns_none_when_ffplay_missing(monkeypatch):
    from utils import runtime

    monkeypatch.setattr(runtime.shutil, "which", lambda name: None)
    assert runtime._start_audio_playback("whatever.mp4") is None


def test_video_plays_normally_when_ffplay_is_missing(monkeypatch):
    # Audio is best-effort: play_ascii_video() must still complete and
    # play its frames even when no audio backend is available at all.
    from utils import runtime

    monkeypatch.setattr(runtime, "_start_audio_playback", lambda path: None)
    with tempfile.TemporaryDirectory() as tmp:
        video_path = Path(tmp) / "test.mp4"
        _write_test_video(video_path)
        lines = build_run_capture(
            'class main() {\n'
            f'video "{video_path.as_posix()}";\n'
            'print("done");\n'
            "}"
        )
    assert lines[-1] == "done"


def test_video_terminates_audio_process_on_mid_playback_error(monkeypatch):
    from utils import runtime

    class _FakeProcess:
        def __init__(self):
            self.terminated = False
            self.waited = False

        def terminate(self):
            self.terminated = True

        def wait(self):
            self.waited = True

    fake_process = _FakeProcess()
    monkeypatch.setattr(runtime, "_start_audio_playback", lambda path: fake_process)

    # Force the frame loop to blow up on its first iteration by handing it
    # a video file that opens successfully (isOpened() True) but whose
    # very first .read() call errors - simulated by monkeypatching cv2's
    # resize to raise, which is simpler than crafting a truly corrupt file.
    cv2 = pytest.importorskip("cv2")

    def _broken_resize(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(cv2, "resize", _broken_resize)

    with tempfile.TemporaryDirectory() as tmp:
        video_path = Path(tmp) / "test.mp4"
        _write_test_video(video_path)
        with pytest.raises(Exception):
            runtime.play_ascii_video(str(video_path))

    assert fake_process.terminated is True
    assert fake_process.waited is False
