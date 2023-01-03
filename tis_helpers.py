import enum
from ast_nodes import *


class ExecutionError(Exception):
    """Represents an error when executing TIS-py00 code."""

    def __init__(self, message: str = "Was not able to execute TIS-py00 code."):
        self.message = message

    def __str__(self):
        return self.message


class TISSyntaxError(ExecutionError):
    """Represents an error in the TIS semantic syntax, that is, valid lexable and parsable code, 
    but not valid semantics. An example is 'mov 10, 10'."""
    pass


class NodeWriteState(enum.IntEnum):
    READABLE = 0
    WILL_BE_READABLE = 1
    RUNNING = 2
    WILL_BE_RUNNING = 3


def validate_node(node):
    """Validates an entire TIS node. Raises a TISSyntaxError if the validation failed, otherwise returns None."""
    for ast_node in node.ast:
        result = validate_instruction(ast_node)

        # If the result wasn't None, and it didn't raise a TISSyntaxError,
        # we know we have to validate check in the label table for the return value
        if result is not None:
            if node.label_table.get(result, None) is None:
                raise TISSyntaxError("Was not able to find label for reference {0}.".format(result))


# The dictionary of instruction opcodes to arguments of the instr_check functions. If an opcode isn't in this dict, it's manually checked
opcode_check_dict = {
    "mov": (2, ((IntegerLiteral, PortLiteral, RegisterLiteral), (PortLiteral, RegisterLiteral))),
    "nop": (0,),
    "swp": (0,),
    "swt": (1, (IntegerLiteral, PortLiteral, RegisterLiteral)),
    "sav": (0,),
    "add": (1, (IntegerLiteral, PortLiteral, RegisterLiteral)),
    "sub": (1, (IntegerLiteral, PortLiteral, RegisterLiteral)),
    "neg": (0,),
    "jmp": (1, LabelReference),
    "jez": (1, LabelReference),
    "jnz": (1, LabelReference),
    "jgz": (1, LabelReference),
    "jlz": (1, LabelReference),
    "jro": (1, (IntegerLiteral, PortLiteral, RegisterLiteral))
}


def validate_instruction(node):
    """Validates an ast_node. Raises a TISSyntaxError if the validation failed, otherwise returns None."""

    # We determine what ast node it is
    if type(node) == NArgumentInstruction:

        # We try to check in the opcode_check_dict
        check_args = opcode_check_dict.get(node.op, None)

        if check_args is not None:
            # We check with the provided args
            instr_arg_num_check(node, check_args[0])
            if len(check_args) > 1:
                # We convert the check_args so they're uniform
                if type(check_args[1]) is tuple:
                    if type(check_args[1][0]) is not tuple:
                        check_args = (check_args[0], ((*check_args[1],),))
                else:
                    check_args = (check_args[0], ((check_args[1],),))

                for inx, arg in enumerate(node.args):
                    print(arg, inx)
                    instr_arg_type_check(arg, check_args[1][inx])
            return

        # We have a switch statement for determining what instruction it is if it isn't in the opcode_check_dict
        if node.op == "hcf":
            raise TISSyntaxError("You can't have halt-and-catch-fire instructions in a program.")

    elif type(node) == LabelReference:
        # We return the label name so the outer loop can validate it
        return node.name


def instr_arg_type_check(node: NArgumentInstruction, _type):
    """Raises a TISSyntaxError if the passed instruction argument (regular ast_node) isn't of _type, 
    or if the type of the passed node is not in _type."""
    if type(_type) is tuple:
        if type(node) not in _type:
            raise TISSyntaxError(
                "Type of instruction argument was {0}, but had to be one of {1}.".format(type(node), _type))
    else:
        if type(node) is not _type:
            raise TISSyntaxError(
                "Type of instruction argument was {0}, but had to be {1}.".format(type(node), _type))


def instr_arg_num_check(node: NArgumentInstruction, num: int):
    """Raises a TISSyntaxError if the passed node doesn't have num number of arguments."""
    if len(node.args) is not num:
        raise TISSyntaxError("{0} instruction did not have required {1} arguments, it had {2}."
                             .format(node.op.capitalize(), num, len(node.args)))
