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


class EvList(list):
    # A plain Python list, tagged with the declared element type of a
    # list<type> (None for an untyped `list`). The parser already rejects
    # a type-mismatched *literal* at parse time (list<int> x: [1, "y"];),
    # but .append(expr)/list[i] = expr; can carry an arbitrary runtime
    # value the parser can't see through - element_type is what lets the
    # VM/interpreter catch a mismatch there too, the same way ptr<type>
    # and arithmetic are runtime-checked beyond what's staticly knowable.
    def __init__(self, iterable=(), element_type: str | None = None):
        super().__init__(iterable)
        self.element_type = element_type


ELEMENT_TYPE_CHECK = {
    "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "float": lambda v: isinstance(v, float),
    "bool": lambda v: isinstance(v, bool),
    "str": lambda v: isinstance(v, str),
}


def check_element_type(target, value, action: str) -> None:
    element_type = getattr(target, "element_type", None)
    if element_type is None:
        return
    if not ELEMENT_TYPE_CHECK[element_type](value):
        raise EvansLangError(
            f"Cannot {action} a {type(value).__name__} into "
            f"list<{element_type}>"
        )


def display(value):
    if isinstance(value, Cell):
        return f"ptr@{id(value):x}"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(_display_element(element) for element in value) + "]"
    return value


def _display_element(value) -> str:
    # Like display(), but always returns a str (rather than passing an
    # int/float straight through) since it's building one comma-joined
    # str for the whole list - and quotes strings so "hi" is
    # distinguishable from an unquoted identifier/number in the output.
    if isinstance(value, str):
        return f'"{value}"'
    displayed = display(value)
    return displayed if isinstance(displayed, str) else str(displayed)


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
