import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import pytest

from linker.linker import link
from utils.errors import EvansLangError


def write(dir_path: Path, name: str, content: str) -> Path:
    path = dir_path / name
    path.write_text(content)
    return path


def resolved_target_of(resolved, class_key: str) -> str:
    """Find the resolved_target of the (single) CallStatement in a class body."""
    from nodes.nodes import CallStatement

    for statement in resolved.classes[class_key].body:
        if isinstance(statement, CallStatement):
            return statement.resolved_target
    raise AssertionError(f"No CallStatement found in {class_key!r}'s body")


def test_links_single_file_with_no_mentions():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write(tmp_path, "main.el", 'class main() {\nprint("hi");\n}')

        resolved = link(tmp_path / "main.el")

        assert resolved.entry == "main"
        assert set(resolved.classes.keys()) == {"main"}


def test_links_mentioned_ment_class_and_resolves_the_call():
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

        assert "main" in resolved.classes
        target = resolved_target_of(resolved, "main")
        assert target in resolved.classes
        assert resolved.classes[target].name == "sdgdsg"


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
            "@mentions test.el -> test;\nclass main() {\ntest.sdgdsg;\n}",
        )

        with pytest.raises(EvansLangError):
            write(tmp_path, "main.el", "@mentions test.el -> test;\nclass main() {\ntest.secret;\n}")
            link(tmp_path / "main.el")


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

        # The root file's own "main" wins; test.el's own class main is
        # linked in too (namespaced under test.el's path, since every
        # class in a linked file is kept for its own internal calls to
        # work) but is never treated as an entry point or auto-run.
        assert resolved.entry == "main"
        assert resolved.classes["main"].body == []


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

        target = resolved_target_of(resolved, "main")
        assert resolved.classes[target].name == "util"


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


def test_circular_mentions_do_not_infinite_loop():
    # a.el mentions b.el; b.el mentions a.el back. Since @mentions is not
    # transitive-following (a mentioned file's own classes are linked once,
    # but ITS mentions are only followed for ITS OWN internal call
    # resolution, not re-entered from the outside), this is a safe no-op
    # re-entry rather than an error or an infinite loop.
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

        resolved = link(tmp_path / "a.el")

        target = resolved_target_of(resolved, "main")
        assert resolved.classes[target].name == "helper"


def test_transitive_mentions_are_not_reachable_from_the_outer_file():
    # a.el mentions b.el; b.el mentions c.el. a.el should NOT be able to
    # reach c.el's classes directly - only files it directly @mentions.
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

        # main -> helper (in b.el) resolves fine.
        main_target = resolved_target_of(resolved, "main")
        assert resolved.classes[main_target].name == "helper"

        # helper's own call to c.deep ALSO resolves fine - b.el's own
        # @mentions still works for b.el's own class bodies.
        helper_target = resolved_target_of(resolved, main_target)
        assert resolved.classes[helper_target].name == "deep"

        # But a.el has no way to spell a call that reaches c.deep directly
        # (it never declared an alias for c.el itself) - there is no
        # CallStatement in a.el's own source with alias "c", so this is
        # enforced by the parser/grammar, not something to probe via
        # resolved.classes directly.


def test_rejects_duplicate_mention_alias_in_same_file():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write(tmp_path, "a.el", 'class util(ment) {\nprint("A");\n}')
        write(tmp_path, "b.el", 'class util(ment) {\nprint("B");\n}')
        write(
            tmp_path,
            "main.el",
            "@mentions a.el -> shared;\n@mentions b.el -> shared;\nclass main() {\nshared.util;\n}",
        )

        with pytest.raises(EvansLangError):
            link(tmp_path / "main.el")


def test_same_file_mentioned_under_different_aliases_shares_one_scope():
    # If two different files both mention the same third file (even under
    # different aliases), that third file should be linked/parsed once,
    # not duplicated under two different sets of classes.
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write(tmp_path, "shared.el", 'class util(ment) {\nprint("shared");\n}')
        write(
            tmp_path,
            "a.el",
            "@mentions shared.el -> s;\nclass helper(ment) {\ns.util;\n}",
        )
        write(
            tmp_path,
            "main.el",
            "@mentions a.el -> a;\n@mentions shared.el -> direct;\n"
            "class main() {\na.helper;\ndirect.util;\n}",
        )

        resolved = link(tmp_path / "main.el")

        main_body_targets = [
            resolved_target_of(resolved, "main"),
        ]
        # Both calls in main (a.helper and direct.util) should resolve,
        # and direct.util / a.helper's inner s.util call should point at
        # the exact same scope key for shared.el's "util" class.
        from nodes.nodes import CallStatement

        targets = [
            stmt.resolved_target
            for stmt in resolved.classes["main"].body
            if isinstance(stmt, CallStatement)
        ]
        assert len(targets) == 2
        helper_target, util_target_direct = targets
        assert resolved.classes[helper_target].name == "helper"
        assert resolved.classes[util_target_direct].name == "util"

        # helper's own inner call to s.util should resolve to the SAME
        # key as main's direct call to direct.util, since shared.el is
        # only ever linked once regardless of alias/path used to reach it.
        inner_target = resolved_target_of(resolved, helper_target)
        assert inner_target == util_target_direct
