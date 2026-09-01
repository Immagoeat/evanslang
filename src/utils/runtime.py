from utils.errors import EvansLangError


class Cell:
    # A boxed variable slot, shared by the VM and the interpreter. Every
    # declared variable's storage is a Cell rather than a raw value, so
    # &x (address-of) can push the Cell itself as a first-class pointer
    # value: *p (dereference) reads cell.value, *p = v (deref-assignment)
    # writes cell.value, and both observe/mutate whatever x currently
    # holds even after x's own later assignments replace cell.value.
    def __init__(self, value=None):
        self.value = value

    def __repr__(self):
        return f"Cell({self.value!r})"


def display(value):
    if isinstance(value, Cell):
        return f"ptr@{id(value):x}"
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def parse_as(text: str, target_type: str):
    if target_type == "str":
        return text
    if target_type == "int":
        try:
            return int(text)
        except ValueError:
            raise EvansLangError(f"Cannot parse {text!r} as an int")
    if target_type == "float":
        try:
            return float(text)
        except ValueError:
            raise EvansLangError(f"Cannot parse {text!r} as a float")
    if target_type == "bool":
        if text == "true":
            return True
        if text == "false":
            return False
        raise EvansLangError(f"Cannot parse {text!r} as a bool")
    raise EvansLangError(f"Unknown parse target type {target_type!r}")
