from ir.ir import OpCode
from ir.ir import Program as IrProgram
from utils.errors import EvansLangError
from utils.runtime import display, parse_as


MAX_CALL_DEPTH = 1000


class VM:
    def __init__(self):
        self.stack = []
        self.variables = {}
        self.call_stack = []
        # Each entry is (catch_pc, stack_depth, call_depth): where to jump
        # on a thrown/raised EvansLangError, and the stack/call_stack
        # lengths to truncate back to first, so a throw from arbitrarily
        # deep inside the try body (including inside called classes)
        # unwinds cleanly to the state the VM was in when the try began.
        self.handler_stack = []

    def run(self, program: IrProgram):
        pc = 0
        instructions = program.instructions
        while pc < len(instructions):
            try:
                pc = self._dispatch(pc, instructions[pc])
            except EvansLangError as error:
                if not self.handler_stack:
                    raise
                catch_pc, stack_depth, call_depth = self.handler_stack.pop()
                del self.stack[stack_depth:]
                del self.call_stack[call_depth:]
                self.stack.append(error.message)
                pc = catch_pc
                continue
            if pc is None:
                return

    def _dispatch(self, pc: int, instruction) -> int | None:
        if instruction.opcode == OpCode.PUSH_CONST:
            self.stack.append(instruction.operand)
        elif instruction.opcode == OpCode.STORE:
            self.variables[instruction.operand] = self.stack.pop()
        elif instruction.opcode == OpCode.LOAD:
            if instruction.operand not in self.variables:
                raise EvansLangError(
                    f"Undefined variable {instruction.operand!r}"
                )
            self.stack.append(self.variables[instruction.operand])
        elif instruction.opcode == OpCode.INPUT:
            prompt = self.stack.pop()
            self.stack.append(input(prompt))
        elif instruction.opcode == OpCode.PARSE:
            self.stack.append(parse_as(self.stack.pop(), instruction.operand))
        elif instruction.opcode == OpCode.POP:
            self.stack.pop()
        elif instruction.opcode == OpCode.PRINT:
            print(display(self.stack.pop()))
        elif instruction.opcode == OpCode.EQ:
            right = self.stack.pop()
            left = self.stack.pop()
            self.stack.append(left == right)
        elif instruction.opcode == OpCode.NEQ:
            right = self.stack.pop()
            left = self.stack.pop()
            self.stack.append(left != right)
        elif instruction.opcode == OpCode.LT:
            right = self.stack.pop()
            left = self.stack.pop()
            self.stack.append(self._compare(left, right, "<"))
        elif instruction.opcode == OpCode.LTE:
            right = self.stack.pop()
            left = self.stack.pop()
            self.stack.append(self._compare(left, right, "<="))
        elif instruction.opcode == OpCode.GT:
            right = self.stack.pop()
            left = self.stack.pop()
            self.stack.append(self._compare(left, right, ">"))
        elif instruction.opcode == OpCode.GTE:
            right = self.stack.pop()
            left = self.stack.pop()
            self.stack.append(self._compare(left, right, ">="))
        elif instruction.opcode == OpCode.AND:
            right = self.stack.pop()
            left = self.stack.pop()
            self.stack.append(bool(left) and bool(right))
        elif instruction.opcode == OpCode.OR:
            right = self.stack.pop()
            left = self.stack.pop()
            self.stack.append(bool(left) or bool(right))
        elif instruction.opcode == OpCode.NOT:
            value = self.stack.pop()
            self.stack.append(not value)
        elif instruction.opcode == OpCode.NEG:
            value = self.stack.pop()
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise EvansLangError(
                    f"Cannot negate a {type(value).__name__}"
                )
            self.stack.append(-value)
        elif instruction.opcode == OpCode.ADD:
            right = self.stack.pop()
            left = self.stack.pop()
            self.stack.append(self._arithmetic(left, right, "+"))
        elif instruction.opcode == OpCode.SUB:
            right = self.stack.pop()
            left = self.stack.pop()
            self.stack.append(self._arithmetic(left, right, "-"))
        elif instruction.opcode == OpCode.MUL:
            right = self.stack.pop()
            left = self.stack.pop()
            self.stack.append(self._arithmetic(left, right, "*"))
        elif instruction.opcode == OpCode.DIV:
            right = self.stack.pop()
            left = self.stack.pop()
            if right == 0:
                raise EvansLangError("Division by zero")
            self.stack.append(self._arithmetic(left, right, "/"))
        elif instruction.opcode == OpCode.JUMP_IF_FALSE:
            condition = self.stack.pop()
            if not condition:
                return pc + instruction.operand
            return pc + 1
        elif instruction.opcode == OpCode.JUMP:
            return pc + instruction.operand
        elif instruction.opcode == OpCode.CALL:
            if len(self.call_stack) >= MAX_CALL_DEPTH:
                raise EvansLangError(
                    f"Call stack exceeded {MAX_CALL_DEPTH} deep "
                    "(likely unbounded recursion)"
                )
            self.call_stack.append(pc + 1)
            return instruction.operand
        elif instruction.opcode == OpCode.RETURN:
            if not self.call_stack:
                raise EvansLangError("Return with no active call")
            return self.call_stack.pop()
        elif instruction.opcode == OpCode.TRY_BEGIN:
            self.handler_stack.append(
                (pc + instruction.operand, len(self.stack), len(self.call_stack))
            )
        elif instruction.opcode == OpCode.TRY_END:
            self.handler_stack.pop()
        elif instruction.opcode == OpCode.THROW:
            value = self.stack.pop()
            if not isinstance(value, str):
                raise EvansLangError(
                    f"Cannot throw a {type(value).__name__} (expected str)"
                )
            raise EvansLangError(value)
        elif instruction.opcode == OpCode.HALT:
            return None
        else:
            raise NotImplementedError(f"Unknown opcode: {instruction.opcode}")
        return pc + 1

    def _compare(self, left, right, operator: str) -> bool:
        try:
            if operator == "<":
                return left < right
            if operator == "<=":
                return left <= right
            if operator == ">":
                return left > right
            return left >= right
        except TypeError:
            raise EvansLangError(
                f"Cannot compare {type(left).__name__} with {type(right).__name__} using {operator!r}"
            )

    def _arithmetic(self, left, right, operator: str):
        try:
            if operator == "+":
                return left + right
            if operator == "-":
                return left - right
            if operator == "*":
                return left * right
            if isinstance(left, int) and isinstance(right, int):
                return left // right
            return left / right
        except TypeError:
            raise EvansLangError(
                f"Cannot apply {operator!r} to {type(left).__name__} and {type(right).__name__}"
            )
