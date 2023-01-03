import ast_nodes as ast_n
from tis_lexer import TokenType, lex, TokenDef, Token

import collections

"""Parses the TIS-Py00 tokens into an AST."""


class ParserError(Exception):
    """An error in parsing a token stream."""

    def __init__(self, message, *tokens):
        self.message = message
        self.tokens = tokens

    def __str__(self):
        if len(self.tokens) == 0:
            return self.message
        return "Characters {0} - {1}: {2}".format(self.tokens[0].slice.start, self.tokens[-1].slice.stop - 1,
                                                  self.message)


class MultiStack(object):
    """This class is a stack implementation with a deque for the cursor, so you can push and pop the cursor."""

    def __init__(self, items):
        if not isinstance(items, list):
            self._items = [items]
        else:
            self._items = items
        self._cursor = 0
        self._cursor_stack = collections.deque()

    def peek(self):
        """Returns the top of the current deque, doesn't pop it."""
        if self._cursor >= len(self._items):
            raise IndexError("Cursor is outside stack.")
        return self._items[self._cursor]

    def pop(self):
        """Does a pop for the cursor."""

        # Peek to get the value to return
        val = self.peek()

        # Increase the cursor, as to simulate an actual pop
        self._cursor += 1

        return val

    def push_cursor(self):
        self._cursor_stack.append(self._cursor)

    def pop_cursor(self):
        self._cursor = self._cursor_stack.pop()


def filter_token_stack(stack: MultiStack):
    """This method filters out all unnecessary tokens from a token stack, so we don't have to handle whitespace."""
    new_stack = MultiStack([item for item in stack._items if (item.type.name not in ("WHITESPACE", "COMMENT"))])
    new_stack._cursor = stack._cursor
    new_stack._cursor_stack = stack._cursor_stack
    return new_stack


class ParserBase(object):
    """A base class for all parsers of tokens."""

    def __init__(self, token_stack: MultiStack):
        self.token_stack = token_stack
        self.node = self.parse()

    def parse(self):
        """Parses the token stack."""
        raise NotImplementedError

    def pop_expecting(self, type_):
        """Pops a token from the token stack, and raises if its type isn't the specified one."""
        next_token = self.token_stack.pop()
        # We check if the type_ is a sequence
        if hasattr(type_, "__iter__") and not isinstance(type_, TokenDef):
            if next_token.type not in type_:
                raise ParserError("Unexpected token: Was expecting one of {0}, but got {1}.".format(
                    ", ".join([str(val) for val in type_]), next_token),
                    next_token)
        elif next_token.type is not type_:
            raise ParserError("Unexpected token: Was expecting {0}, but got {1}.".format(type_, next_token.type),
                              next_token)
        return next_token


class InstructionStatement(ParserBase):
    def parse(self):
        # We get the instruction
        instruction_token = self.pop_expecting(TokenType.INSTRUCTION)

        # The list of argument ast nodes we have
        instruction_ast_arguments = []

        # Indicating that the last gotten token was a separator
        last_was_sep = True

        # We continue getting all arguments to the instruction until we don't encounter a
        while True:
            # We get the next token in the stream and return if we reach the end of the token stack
            try:
                next_token = self.token_stack.peek()
            except IndexError:
                return ast_n.NArgumentInstruction(instruction_token.value, instruction_ast_arguments)

            # We check if the token is one we are able to parse with this statement
            # We do the dirty *ing of the port defs because we need to check with each of them aswell
            if next_token.type not in (
            TokenType.SEPARATOR, TokenType.INTEGER, *TokenType.PORT, TokenType.REGISTER, TokenType.LABEL_REF):
                return ast_n.NArgumentInstruction(instruction_token.value, instruction_ast_arguments)

            # We want a separator after each argument
            if len(instruction_ast_arguments) > 0:
                if not (last_was_sep or next_token.type == TokenType.SEPARATOR):
                    # We do the parsing for the new token
                    raise ParserError("Unexpected token: Was expecting separator, but got non-separator.", next_token)

            # If this token is a separator we continue, but mark that it was
            if next_token.type == TokenType.SEPARATOR:
                last_was_sep = True
                # We need to increment the cursor here
                self.token_stack.pop()
                continue
            else:
                last_was_sep = False

            # We parse the token and add that ast node to the arguments list
            if next_token.type == TokenType.INTEGER:
                instruction_ast_arguments.append(IntegerLiteralExpression(MultiStack(next_token)).node)
            elif next_token.type in TokenType.PORT:
                instruction_ast_arguments.append(PortLiteralExpression(MultiStack(next_token)).node)
            elif next_token.type == TokenType.REGISTER:
                instruction_ast_arguments.append(RegisterLiteralExpression(MultiStack(next_token)).node)
            elif next_token.type == TokenType.LABEL_REF:
                instruction_ast_arguments.append(LabelReferenceExpression(MultiStack(next_token)).node)

            # We need to increment the cursor here
            self.token_stack.pop()


class IntegerLiteralExpression(ParserBase):
    def parse(self):
        int_token = self.pop_expecting(TokenType.INTEGER)
        return ast_n.IntegerLiteral(int_token.value)


class PortLiteralExpression(ParserBase):
    def parse(self):
        port_token = self.pop_expecting(TokenType.PORT)
        return ast_n.PortLiteral(port_token.value)


class RegisterLiteralExpression(ParserBase):
    def parse(self):
        reg_token = self.pop_expecting(TokenType.REGISTER)
        return ast_n.RegisterLiteral(reg_token.value)


class NodeMarkerStatement(ParserBase):
    def parse(self):
        node_m_token = self.pop_expecting(TokenType.NODE_SPECIFIER)
        return ast_n.NodeMarker(node_m_token.value, SingleNodeASTParser(self.token_stack))


class LabelStatement(ParserBase):
    def parse(self):
        label_token = self.pop_expecting(TokenType.LABEL)
        return ast_n.Label(label_token.value)


class LabelReferenceExpression(ParserBase):
    def parse(self):
        label_token = self.pop_expecting(TokenType.LABEL_REF)
        return ast_n.LabelReference(label_token.value)


class SingleNodeASTParser(ParserBase):
    """This parser parses tokens for a single node, that is, without any node markers. This means it only checks for labels, comments, and instructions.
    It returns a list of ast_nodes, that might be empty."""

    def parse(self):

        # All ast_nodes for this node
        nodes = []

        while True:
            # We get the next node
            try:
                next_token = self.token_stack.peek()
            except IndexError:
                return ast_n.SingleNodeAST(nodes)

            # We parse it appropriately and add it to the nodes list
            if next_token.type in TokenType.INSTRUCTION:
                nodes.append(InstructionStatement(self.token_stack).node)
            elif next_token.type == TokenType.LABEL:
                nodes.append(LabelStatement(self.token_stack).node)
            elif next_token.type == TokenType.NODE_SPECIFIER:
                # We return the nodes
                return ast_n.SingleNodeAST(nodes)
            elif next_token.type == TokenType.COMMENT:
                # We pass on comments, but not on anything else, since we want to not run on invalid code
                pass
            else:
                raise ParserError(
                    "Expected valid token, found neither instruction, label, nor comment. Found {0}.".format(
                        next_token.type.name), next_token)


class MultiNodeParser(ParserBase):
    """This parser parses for each node, and stores the nodes' asts in a dict. It filters the input nodes."""

    def parse(self):

        # We filter the tokens
        self.token_stack = filter_token_stack(self.token_stack)

        # The dict we store each node's ast in
        node_asts = {}

        while True:
            # We get the next node
            try:
                next_token = self.token_stack.pop()
            except IndexError:
                self.ast_node = ast_n.ASTRoot(node_asts)
                return ast_n.ASTRoot(node_asts)

            # We check if the token is something we should ignore and continue on, or a node specifier
            if next_token.type == TokenType.NODE_SPECIFIER:
                # We push our cursor to be able to continue even if the single node parser consumes the stack
                self.token_stack.push_cursor()

                # We parse that node's subtree
                node_asts[next_token.value] = SingleNodeASTParser(self.token_stack).node

                # We pop back our cursor
                self.token_stack.pop_cursor()
            else:
                continue


def parse(text):
    return MultiNodeParser(MultiStack(lex(text))).ast_node
