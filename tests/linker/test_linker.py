import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import pytest

from linker.linker import SEPARATOR, link
from utils.errors import EvansLangError


def write(dir_path: Path, name: str, content: str) -> Path:
    path = dir_path / name
    path.write_text(content)
    return path


def test_links_single_file_with_no_mentions():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write(tmp_path, "main.el", 'class main() {\nprint("hi");\n}')

        resolved = link(tmp_path / "main.el")

        assert resolved.entry == "main"
        assert set(resolved.classes.keys()) == {"main"}


def test_links_mentioned_ment_class_under_alias():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write(
            tmp_path,
            "test.el",
            'class sdgdsg(ment) {\nprint("hi");\n}',
        )
        write(
            tmp_path,
            "main.el",
            "@mentions test.el -> test;\nclass main() {\ntest.sdgdsg;\n}",
        )

        resolved = link(tmp_path / "main.el")

        assert f"test{SEPARATOR}sdgdsg" in resolved.classes
        assert "main" in resolved.classes


def test_non_ment_classes_are_not_reachable_from_other_files():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write(
            tmp_path,
            "test.el",
            'class sdgdsg(ment) {}\nclass secret() {\nprint("hi");\n}',
        )
        write(
            tmp_path,
            "main.el",
            "@mentions test.el -> test;\nclass main() {}",
        )

        resolved = link(tmp_path / "main.el")

        assert f"test{SEPARATOR}sdgdsg" in resolved.classes
        assert f"test{SEPARATOR}secret" not in resolved.classes


def test_mentioned_files_own_main_is_not_included_as_entry():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write(
            tmp_path,
            "test.el",
            'class util(ment) {}\nclass main() {\nprint("should never run");\n}',
        )
        write(
            tmp_path,
            "main.el",
            "@mentions test.el -> test;\nclass main() {}",
        )

        resolved = link(tmp_path / "main.el")

        # The root file's own "main" wins; test.el's main is not merged in
        # under any name since it isn't ment and mentioned-file classes
        # only surface under their alias.
        assert resolved.entry == "main"
        assert resolved.classes["main"] is not None


def test_mentioned_file_without_main_is_valid():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write(tmp_path, "lib.el", 'class util(ment) {\nprint("hi");\n}')
        write(
            tmp_path,
            "main.el",
            "@mentions lib.el -> lib;\nclass main() {\nlib.util;\n}",
        )

        resolved = link(tmp_path / "main.el")

        assert f"lib{SEPARATOR}util" in resolved.classes


def test_raises_when_root_file_has_no_main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write(tmp_path, "lib.el", 'class util(ment) {\nprint("hi");\n}')

        with pytest.raises(EvansLangError):
            link(tmp_path / "lib.el")


def test_raises_on_missing_mentioned_file():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write(
            tmp_path,
            "main.el",
            "@mentions missing.el -> m;\nclass main() {}",
        )

        with pytest.raises(EvansLangError):
            link(tmp_path / "main.el")


def test_raises_on_circular_mentions():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write(
            tmp_path,
            "a.el",
            "@mentions b.el -> b;\nclass main() {\nb.helper;\n}",
        )
        write(
            tmp_path,
            "b.el",
            "@mentions a.el -> a;\nclass helper(ment) {}",
        )

        with pytest.raises(EvansLangError):
            link(tmp_path / "a.el")


def test_transitive_mentions_are_not_included():
    # a.el mentions b.el; b.el mentions c.el. a.el should NOT automatically
    # see c.el's classes - only files it directly @mentions.
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write(tmp_path, "c.el", 'class deep(ment) {\nprint("hi");\n}')
        write(
            tmp_path,
            "b.el",
            "@mentions c.el -> c;\nclass helper(ment) {\nc.deep;\n}",
        )
        write(
            tmp_path,
            "a.el",
            "@mentions b.el -> b;\nclass main() {\nb.helper;\n}",
        )

        resolved = link(tmp_path / "a.el")

        assert f"b{SEPARATOR}helper" in resolved.classes
        assert f"c{SEPARATOR}deep" in resolved.classes
        # b's own call to c.deep resolves under b's alias namespace ("c"),
        # which only exists because b.el declared its own @mentions - a.el
        # never sees an alias literally named "c" itself.
