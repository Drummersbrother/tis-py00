from tis_helpers import *


class TISNode(object):
    """Represents a single node in the grid."""

    def __init__(self, id: int, grid_height: int, grid_width: int, ast: SingleNodeAST = None):
        """Creates the Node, with specified ids for the nodes in different directions."""

        # The id of this node
        self.id = id

        # A lookup dict for id to node, only filled on runtime
        self.node_dict = None

        # The abstract syntax tree
        self.ast = [] if ast is None else ast.ast

        # A lookup for the ast. The values are indices into our ast, and the indices are the index of the instruction the ast index points to.
        # Basically, finds the index of the Nth instruction node
        self.ast_instr_real_lookup = []

        # We populate the instruction lookup
        for ast_inx, ast_node in enumerate(self.ast):
            if type(ast_node) == NArgumentInstruction:
                self.ast_instr_real_lookup.append(ast_inx)

        # A reverse lookup of the ast_instr_real_lookup, note that this is a dict and not a list, since it's a strict reverse lookup
        self.ast_real_instr_lookup = {}

        # We populate the instruction lookup
        for instr_inx, instr_node_inx in enumerate(self.ast_instr_real_lookup):
            self.ast_real_instr_lookup[instr_node_inx] = instr_inx

        # For performance reasons, we precompute this
        self.ast_len = len(self.ast)

        # The instruction we're at, an index into the ast
        self.instruction_pointer = 0

        # Port ids, calculated from our id and the grid sizes
        self.up_id = id - grid_width if not id - grid_width < 0 else None
        self.down_id = id + grid_width if id + grid_width < grid_width * grid_height else None
        self.left_id = id - 1 if (id > 0) and (id % grid_width is not 0) else None
        self.right_id = id + 1 if (id + 1 < grid_width * grid_height) and ((id + 1) % grid_width is not 0) else None

        # A lookup for directions to id
        self.directions = {"UP": self.up_id, "DOWN": self.down_id, "LEFT": self.left_id, "RIGHT": self.right_id}

        # The value at the different ports
        # When there is data at this port, the format is (target_port: int, value: int), where target_port is the uppercase name of the port
        self.port_value = None

        # The port we're waiting for to send something to us, will be uppercase name of the port
        self.wait_port = None

        # A temporary variable set by another node when something is sent to us
        # The format is (port: str, value: int)
        self.sent_value = None

        # The last port something was sent to, will be uppercase name of the port
        self.last_port = None

        # Special values
        self.accs = [0] * 8
        self.baks = [0] * 8

        # The cursor/index into the bak and acc lists
        self._register_cursor = 0

        # We look through our AST and create a lookup table for the labels
        # The table is a lookup for labelname into ast index
        self.label_table = {}
        for inx, node in enumerate(self.ast):
            if type(node) == Label:
                self.label_table[node.name] = inx

        # We validate our ast, if it's valid, this won't output anything, if it's invalid, this will raise a TISSyntaxError
        validate_node(self)

        # The state the node is in
        # This can is one of the NodeWriteState values
        self.state = NodeWriteState.RUNNING

    def __str__(self):
        return "TIS Node, \n\tport ids: {0}, \n\tport value: {1}, \n\taccs: {2}, \n\tbaks: {3}, \n\tregister cursor: {4}, \n\tstate: {5}, " \
               "\n\twait port: {6}, \n\tsent value: {7}, \n\tlast port: {8}, \n\tinstruction pointer: {9}, \n\tcurrent instruction: {10}, \n\tast: {11}".format(
            "up: {0}, down: {1}, left: {2}, right: {3}".format(self.up_id, self.down_id, self.left_id, self.right_id),
            str(self.port_value),
            self.accs,
            self.baks,
            self._register_cursor,
            str(self.state),
            str(self.wait_port),
            str(self.sent_value),
            str(self.last_port),
            str(self.instruction_pointer),
            str(self.ast[self.instruction_pointer]),
            [str(node) for node in self.ast]
        )

    def get_node_with_id(self, _id: int):
        """Returns the node that has a specific id from the list of nodes. Returns None if there isn't one with that id."""
        try:
            return self.node_dict[_id]
        except KeyError:
            return None

    def step(self, *, nodes: dict):
        """Does a singe computational step. It considers all non-None values of the neighbouring nodes to be real nodes."""

        # We compute a lookup table for the nodes, this is for performance reasons
        self.node_dict = nodes

        # We check what ast node is the current one, it has to be an instruction or label, all other are disallowed
        cur_node = self.ast[self.instruction_pointer]

        # If we are waiting for something, we check if we've got it
        if self.wait_port is not None:
            if self.sent_value is not None:

                # We execute the instruction we we're stuck on
                if self.do_instr(cur_node):
                    # We aren't waiting anymore
                    self.wait_port = None

                    # We reset the temp sent value
                    self.sent_value = None

                    # We're no longer waiting, so we go into running mode again and exit this step
                    self.state = NodeWriteState.RUNNING

                    self.incr_instr_pointer()

            return

        elif self.port_value is not None:
            # We're sending something to another node
            # We execute the instruction, and reset the send variables if the sending was completed
            if self.do_instr(cur_node):
                # We reset the port value
                self.port_value = None

                # We're no longer waiting, so we go into running mode again and exit this step
                self.state = NodeWriteState.RUNNING

                self.incr_instr_pointer()

            return

        if type(cur_node) == NArgumentInstruction:

            # We check if we should continue executing
            if self.do_instr(cur_node):
                self.incr_instr_pointer()

        elif type(cur_node) == Label:
            # We increment the instruction pointer, and try stepping again
            self.incr_instr_pointer()
            self.step(nodes=nodes)

        else:
            raise ExecutionError("Invalid code at ast node with id {0}: {1}".format(self.instruction_pointer, cur_node))

    def do_instr(self, instruction_node):
        """Gets an NArgumentInstruction ast node and executes it."""

        # We get the appropriate instruction function to pass this to
        instr_func = getattr(self, "instr_" + instruction_node.op, None)

        # If we couldn't find a function to do it, we raise a NotImplementedError
        if instr_func is None:
            raise NotImplementedError(
                "Was not able to find instruction function for opcode {0}.".format(instruction_node.op))
        else:
            # We return the result of the instruction function
            return instr_func(instruction_node)

    def incr_instr_pointer(self):
        """Increments the instruction pointer and handles wrap-around so we loop the whole ast."""
        self.instruction_pointer += 1
        if self.instruction_pointer is self.ast_len:
            self.instruction_pointer = 0

    def get_value_from_port(self, port: str):
        """This function is called whenever we need to get something from another port. It first sets up waiting, and then returns the gotten value.
        It returns None if the port hasn't been transferred to."""

        # We check if we're already waiting for something
        if self.wait_port is not None:
            # We check if we've gotten a value
            if self.sent_value is not None:
                # We set the last_port to be the port we got sent this from
                self.last_port = self.sent_value[0]

                # We reset the port value of the sending node
                self.get_node_with_id(self.directions[self.last_port]).port_value = None

                # We return the value
                return self.sent_value[1]
            else:
                # We haven't gotten a value and we continue waiting, this will actually never happen since this logic is handled in the step function
                return None

        # If the port is NIL, we return 0
        if port == "NIL":
            return 0
        elif port == "LAST":
            # If the port is LAST, we look up the value for last, and block forever if there isn't one
            port = self.last_port
            if port is None:
                return None

        # We set up wait_port properly, and start waiting
        self.wait_port = port
        self.state = NodeWriteState.WILL_BE_RUNNING

    def set_value_to_port(self, port: str, value: int):
        """Sets the value to the port. Returns False until the value has been transferred. Returns True when the value has been transferred."""

        # We set the port value to what we're sending
        self.port_value = (port, value)

        # We set the state to will be running
        self.state = NodeWriteState.WILL_BE_RUNNING

        # We check if the port is a special one
        if port in ("ANY", "LAST", "NIL"):
            if port == "ANY":
                # We check each port in the order the game does
                order = ("UP", "LEFT", "RIGHT", "DOWN")

                # We go through the directions in order
                for direction in order:
                    if self.directions[direction] is not None:
                        # We try to send to the port
                        result = self.set_value_to_port(direction, value)

                        if result:
                            # We were successful in sending to the port
                            return result
                else:
                    # If we weren't successful in sending to the ANY port this step, we return False
                    return False

            elif port == "LAST":
                # We block forever if the node doesn't have a LAST port set, otherwise we send if possible
                if self.last_port is None:
                    return False
                else:
                    # We send to the port that's stored in last_port
                    return self.set_value_to_port(self.last_port, value)
            else:
                # The port is NIL, so we just return, as that is effectively a NOP
                return True

        # We check if there could exist a node to send the value to
        if self.directions[port] is None:
            # There isn't a node at that port, so we basically block forever
            return False

        # The node we send to
        target_node = self.get_node_with_id(self.directions[port])

        # We check if the node has any code, as if it doesn't, it can't ever receive, so we automatically block
        if target_node is None:
            return False

        # We know that the port points to a node with code, so we check what port we should look in (since one node's RIGHT is another's LEFT)
        look_for_port = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}[port]

        # We check if the target node wants a value from us, note that this deals with the case of the node not waiting at all
        if target_node.wait_port in ("ANY", look_for_port):

            # We give the value to the target node
            target_node.sent_value = (look_for_port, value)

            # We return True since we successfully sent the value
            return True

        else:
            # The target node didn't want a value from us
            return False

    # From here the instruction functions are defined
    def instr_mov(self, node: NArgumentInstruction):
        """This opcode moves values to and from different places, called sources and destinations."""

        # We make sure there's only one operand
        if len(node.args) is not 2:
            raise TISSyntaxError(
                "Invalid number of operands in mov instruction. Number should be 2, was {0}.".format(len(node.args)))

        # The source
        source = node.args[0]
        # The destination
        destination = node.args[1]

        # We do different things depending on the type of source
        if type(source) == IntegerLiteral:
            # The source value is simply the int value
            source_val = source.value

        elif type(source) == PortLiteral:
            # We handle port transfers to the source value
            # We get the value
            source_val = self.get_value_from_port(source.name)

            # If the value is None, that means we have to wait more for another node to give us a value
            if source_val is None:
                return

        elif type(source) == RegisterLiteral:
            # The source is acc, so we store acc's value in source_val
            source_val = self.accs[self._register_cursor]

        # We do different things depending on the type of destination. We only allow register and port for destination
        # We do different things depending on the type of source
        if type(destination) == PortLiteral:
            # We handle port transfers of the source val to the destination, and we have already handled port-port movs
            return self.set_value_to_port(destination.name, source_val)

        elif type(destination) == RegisterLiteral:
            # The destination is acc, so we simply store the source_val into acc
            self.accs[self._register_cursor] = source_val

            return True

    def instr_add(self, node: NArgumentInstruction):
        """This opcode adds the operand to acc and stores it in acc."""

        # The operand
        add_operand = node.args[0]

        # We do different things depending on the type of argument
        if type(add_operand) == IntegerLiteral:
            # We simply add to acc
            self.accs[self._register_cursor] += add_operand.value

        elif type(add_operand) == PortLiteral:
            # We handle port transfers
            add_operand_value = self.get_value_from_port(add_operand.name)

            # We check if we got a value from the port
            if add_operand_value is None:
                return

            # We add the value
            self.accs[self._register_cursor] += add_operand_value

        elif type(add_operand) == RegisterLiteral:
            # This means we add acc to itself
            self.accs[self._register_cursor] *= 2

        # We successfully executed the instruction
        return True

    def instr_sub(self, node: NArgumentInstruction):
        """This opcode subtracts the operand to acc and stores it in acc."""

        # The operand
        sub_operand = node.args[0]

        # We do different things depending on the type of argument
        if type(sub_operand) == IntegerLiteral:
            # We simply subtract to acc
            self.accs[self._register_cursor] -= sub_operand.value

        elif type(sub_operand) == PortLiteral:
            # We handle port transfers
            sub_operand_value = self.get_value_from_port(sub_operand.name)

            # We check if we got a value from the port
            if sub_operand_value is None:
                return

            # We subtract the value
            self.accs[self._register_cursor] -= sub_operand_value

        elif type(sub_operand) == RegisterLiteral:
            # This means we set acc to 0
            self.accs[self._register_cursor] = 0

        # We successfully executed the instruction
        return True

    def instr_sav(self, node: NArgumentInstruction):
        """Saves acc into bak."""
        self.baks[self._register_cursor] = self.accs[self._register_cursor]
        return True

    def instr_swt(self, node: NArgumentInstruction):
        """Switches to the specified pair of registers (acc and bak)."""

        # The operand
        swt_operand = node.args[0]

        # We do different things depending on the type of argument
        if type(swt_operand) == IntegerLiteral:

            # We simply switch to the registers specified by the integer value
            swt_operand_value = swt_operand.value

        elif type(swt_operand) == PortLiteral:
            # We handle port transfers
            swt_operand_value = self.get_value_from_port(swt_operand.name)

            # We check if we got a value from the port
            if swt_operand is None:
                return

        else:
            # This means the operand is a RegisterLiteral, we can guarantee this because of the validator
            # This means we switch to the pair pointed to by the previous acc
            swt_operand_value = self.accs[self._register_cursor]

        # We sanity check the value, we only allow positive valid indices
        if not (len(self.accs) > swt_operand_value >= 0):
            raise TISSyntaxError(
                "SWT operand was not in the valid range of registers. Range is {0}-{1} inclusive, operand was {2}."
                    .format(0, len(self.accs), swt_operand_value))

        # We switch to the pair
        self._register_cursor = swt_operand_value

        # We successfully executed the instruction
        return True

    def instr_swp(self, node: NArgumentInstruction):
        """Swaps the current acc with the current bak, does not swap all register."""
        # We simply swap them using python's implicit tuple syntax
        self.accs[self._register_cursor], self.baks[self._register_cursor] = self.baks[self._register_cursor], self.accs[self._register_cursor]
        return True

    def instr_neg(self, node: NArgumentInstruction):
        """Negates acc."""
        # We negate it
        self.accs[self._register_cursor] *= -1
        return True

    @staticmethod
    def instr_nop(*args):
        """Does nothing, simply takes one step."""
        return True

    def instr_jmp(self, node: NArgumentInstruction):
        """Unconditionally jumps to a label."""

        # We change the instruction pointer to the index that the label table lookup gives
        # The validator has checked that the label exists,
        # and that implies that the populating of the label table has created a valid table
        self.instruction_pointer = self.label_table[node.args[0].name]

        # We successfully executed the instruction
        return True

    def instr_jez(self, node: NArgumentInstruction):
        """Jumps to label if acc is 0."""

        # If acc is 0, we execute a jmp instruction with the label given,
        # else, continues execution by returning True
        if self.accs[self._register_cursor] is 0:
            return self.instr_jmp(NArgumentInstruction("jmp", [node.args[0]]))
        return True

    def instr_jnz(self, node: NArgumentInstruction):
        """Jumps to label if acc is not 0."""

        # If acc is not 0, we execute a jmp instruction with the label given,
        # else, continues execution by returning True
        if self.accs[self._register_cursor] is not 0:
            return self.instr_jmp(NArgumentInstruction("jmp", [node.args[0]]))
        return True

    def instr_jgz(self, node: NArgumentInstruction):
        """Jumps to label if acc is greater than 0."""

        # If acc is greater than 0, we execute a jmp instruction with the label given,
        # else, continues execution by returning True
        if self.accs[self._register_cursor] > 0:
            return self.instr_jmp(NArgumentInstruction("jmp", [node.args[0]]))
        return True

    def instr_jlz(self, node: NArgumentInstruction):
        """Jumps to label if acc is less than 0."""

        # If acc is less than 0, we execute a jmp instruction with the label given,
        # else, continues execution by returning True
        if self.accs[self._register_cursor] < 0:
            return self.instr_jmp(NArgumentInstruction("jmp", [node.args[0]]))
        return True

    def instr_jro(self, node: NArgumentInstruction):
        """Jumps operand instructions forwards."""

        # The operand
        jro_operand = node.args[0]

        # We do different things depending on the type of argument
        if type(jro_operand) == IntegerLiteral:
            # We get the integer value
            jro_operand_value = jro_operand.value

        elif type(jro_operand) == PortLiteral:
            # We handle port transfers
            jro_operand_value = self.get_value_from_port(jro_operand.name)

            # We check if we got a value from the port
            if jro_operand_value is None:
                return

        else:
            # Since we execute validated code, we know that the operand is a RegisterLiteral
            # We get the register value
            jro_operand_value = self.accs[self._register_cursor]

        # We use the ast-lookup dict that only counts instructions, as that's what the game does
        # We subtract the operand value because we increment the instruction counter after each successful instruction execution
        self.instruction_pointer = self.ast_instr_real_lookup[self.ast_real_instr_lookup[self.instruction_pointer] + jro_operand_value - 1]

        # We successfully executed the instruction
        return True