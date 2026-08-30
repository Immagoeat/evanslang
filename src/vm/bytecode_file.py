import pickle
from pathlib import Path

from ir.ir import Program as IrProgram

MAGIC = b"EVLC"
VERSION = 1


def write(path: Path, program: IrProgram):
    with open(path, "wb") as f:
        f.write(MAGIC)
        f.write(VERSION.to_bytes(1, "big"))
        pickle.dump(program.instructions, f)


def read(path: Path) -> IrProgram:
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != MAGIC:
            raise ValueError(f"{path} is not a valid evanslang bytecode file")
        version = int.from_bytes(f.read(1), "big")
        if version != VERSION:
            raise ValueError(f"Unsupported bytecode version: {version}")
        instructions = pickle.load(f)
    return IrProgram(instructions)
