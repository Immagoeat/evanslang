import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from codegen.codegen import CodeGenerator
from lexer.lexer import Lexer
from parser.parser import Parser
from utils.errors import EvansLangError
from vm import bytecode_file
from vm.vm import VM


BYTECODE_EXTENSION = ".evlc"


def build(source_path: Path, output_path: Path):
    if output_path.suffix != BYTECODE_EXTENSION:
        output_path = output_path.with_name(output_path.name + BYTECODE_EXTENSION)

    source = source_path.read_text()
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    ir_program = CodeGenerator().generate(program)
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

    try:
        if args.build:
            source_path, output_path = args.build
            written_path = build(Path(source_path), Path(output_path))
            print(f"Built {written_path}")
        elif args.run:
            run(Path(args.run))
    except EvansLangError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
