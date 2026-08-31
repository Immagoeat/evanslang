import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from codegen.codegen import CodeGenerator
from linker.linker import link
from utils.errors import EvansLangError
from vm import bytecode_file
from vm.vm import VM

BOLD_RED = "\033[1;31m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def _use_color() -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    return sys.stderr.isatty()


def print_error(error: EvansLangError, source_path: Path | None = None) -> None:
    color = _use_color()
    kind = getattr(error, "kind", "error")

    if color:
        header = f"{BOLD_RED}{kind}:{RESET} {BOLD}{error.message}{RESET}"
    else:
        header = f"{kind}: {error.message}"
    print(header, file=sys.stderr)

    if error.line is not None:
        location = f"{source_path}:" if source_path else "line "
        location += f"{error.line}:{error.column}"
        if color:
            print(f"{DIM}  at {location}{RESET}", file=sys.stderr)
        else:
            print(f"  at {location}", file=sys.stderr)


BYTECODE_EXTENSION = ".evlc"


def build(source_path: Path, output_path: Path):
    if output_path.suffix != BYTECODE_EXTENSION:
        output_path = output_path.with_name(output_path.name + BYTECODE_EXTENSION)

    resolved = link(source_path)
    ir_program = CodeGenerator().generate(resolved)
    bytecode_file.write(output_path, ir_program)
    return output_path


def run(bytecode_path: Path):
    if not bytecode_path.exists() and bytecode_path.suffix != BYTECODE_EXTENSION:
        candidate = bytecode_path.with_name(bytecode_path.name + BYTECODE_EXTENSION)
        if candidate.exists():
            bytecode_path = candidate

    ir_program = bytecode_file.read(bytecode_path)
    VM().run(ir_program)


def main():
    parser = argparse.ArgumentParser(
        prog="evlng",
        description="evanslang compiler and runtime.",
        epilog=(
            "examples:\n"
            "  evlng --build hello.el hello   Compile hello.el to hello.evlc\n"
            "  evlng --run hello               Execute hello.evlc\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--build",
        nargs=2,
        metavar=("SOURCE", "OUTPUT"),
        help="Compile a .el source file into a bytecode binary",
    )
    group.add_argument(
        "--run", metavar="BINARY", help="Execute a binary produced by --build"
    )
    args = parser.parse_args()

    source_path = Path(args.build[0]) if args.build else None

    try:
        if args.build:
            _, output_path = args.build
            written_path = build(source_path, Path(output_path))
            print(f"Built {written_path}")
        elif args.run:
            run(Path(args.run))
    except EvansLangError as e:
        print_error(e, source_path)
        sys.exit(1)
    except (OSError, ValueError) as e:
        print_error(EvansLangError(str(e)))
        sys.exit(1)


if __name__ == "__main__":
    main()
