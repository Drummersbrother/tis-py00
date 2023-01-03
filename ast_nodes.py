import collections

"""An abstract syntax tree is the tree of actual semantic operations the program executes."""

class IntegerLiteral(collections.namedtuple("IntegerLiteral", "value")):
    """Represents an integer in the code."""

    def to_dict(self):
        """We have a dictionary converting method to be able to convert this into json."""
        return {"type": "IntegerLiteral", "value": int(self.value)}

class NArgumentInstruction(collections.namedtuple("NArgumentInstruction", ("op", "args"))):
    """Represents a TIS-Py00 instruction with an arbitrary number of arguments."""

    def to_dict(self):
        """We have a dictionary converting method to be able to convert this into json."""
        return {"type": "NArgumentInstruction", "op": self.op, "args": [arg_node.to_dict() for arg_node in self.args]}

class NodeMarker(collections.namedtuple("NodeMarker", ("id", "ast_subtree"))):
    """Represents the code that a single node has."""

    def to_dict(self):
        """We have a dictionary converting method to be able to convert this into json."""
        return {"type": "NodeMarker", "id": int(self.id), "value": self.ast_subtree.to_dict()}

class PortLiteral(collections.namedtuple("PortLiteral", "name")):
    """Represents a port in an instruction."""

    def to_dict(self):
        """We have a dictionary converting method to be able to convert this into json."""
        return {"type": "PortLiteral", "value": self.name}

class RegisterLiteral(collections.namedtuple("RegisterLiteral", "name")):
    """Represents a register in an instruction."""

    def to_dict(self):
        """We have a dictionary converting method to be able to convert this into json."""
        return {"type": "RegisterLiteral", "value": self.name}

class Label(collections.namedtuple("Label", "name")):
    """Represents a label definition."""

    def to_dict(self):
        """We have a dictionary converting method to be able to convert this into json."""
        return {"type": "Label", "value": self.name}

class LabelReference(collections.namedtuple("LabelReference", "name")):
    """Represents a label reference."""

    def to_dict(self):
        """We have a dictionary converting method to be able to convert this into json."""
        return {"type": "LabelReference", "value": self.name}

class SingleNodeAST(collections.namedtuple("SingleNodeAST", "ast")):
    """Represents a single node and its code."""

    def to_dict(self):
        """We have a dictionary converting method to be able to convert this into json."""
        return {"type": "SingleNodeAST", "ast": [ast_node.to_dict() for ast_node in self.ast]}

class ASTRoot(collections.namedtuple("ASTRoot", "nodes")):
    """Represents a program with nodes and their code."""

    def to_dict(self):
        """We have a dictionary converting method to be able to convert this into json."""
        return {"type": "ASTRoot", "nodes": {key: val.to_dict() for key, val in self.nodes.items()}}