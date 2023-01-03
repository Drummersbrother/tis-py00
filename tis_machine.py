from tis_node import TISNode
from functools import partial
import curses
import math
import tis_helpers
import tis_parser

def run_src(source: str="@0\nnop", node_height: int=4, node_width: int=5, stdscr=None):
    """Runs TIS-py00 code with an interface. node_height is the number of layers of nodes vertically, 
    and node_width is the number of nodes horizontally"""

    # Curses initialisation step
    stdscr.clear()
    stdscr.idlok(True)
    stdscr.leaveok(False)
    stdscr.scrollok(False)
    curses.curs_set(False)
    lines = curses.LINES
    cols = curses.COLS
    node_h = 3
    node_w = 3
    # Since we are going to divide the screen into 10 areas according to the figure below,
    # we calculate each windows' offset and dimensions.
    # This is the layout of nodes when trying to view the fifth node
    # --------------------------------------------
    # |             |              |             |
    # |      1      |       2      |      3      |
    # |             |              |             |
    # |------------------------------------------|
    # |             |              |             |
    # |      4      |       5      |      6      |
    # |             |              |             |
    # |------------------------------------------|
    # |             |              |             |
    # |      7      |       8      |      9      |
    # |             |              |             |
    # |------------------------------------------|
    # |                                          |
    # |               Main console               |
    # |           Results vs Expected            |
    # |                                          |
    # --------------------------------------------
    # We have node-name --> tuple(height, width, begin_y, begin_x), note that the order is y, x, not x, y.
    dimensions = {}
    quarter_h = math.floor(lines / 4)
    third_w = math.floor(cols / 3)
    # Creating the tiled node-windows' dimensions
    for i in range(node_h):
        for j in range(node_w):
            dimensions[3*i + j + 1] = (
                quarter_h,
                third_w,
                i * quarter_h,
                j * third_w
            )
    # This has the same keys as the dimension dictionary
    windows = {}
    for node, dims in dimensions.items():
        windows[node] = curses.newwin(*dims)
        windows[node].move(0, 0)
    # We add the console window
    windows["cons"] = curses.newwin(quarter_h, cols - 2, node_h * quarter_h, 0)
    windows["cons"].border()
    cons_out_h = quarter_h - 3
    cons_out_w = cols - 4
    windows["cons_out"] = windows["cons"].derwin(cons_out_h, cons_out_w, 2, 1)
    windows["cons_out"].scrollok(False)
    windows["cons"].addstr(1, int((cols / 2) - 8), "This is the console:", curses.A_STANDOUT)
    windows["std"] = stdscr

    # Refreshes the whole screen efficiently
    def refresh():
        for window in windows.values():
            window.noutrefresh()
        curses.doupdate()
    refresh()

    # Descriptions for each node
    node_descs = {
        0: "upper left",
        1: "up",
        2: "upper right",
        3: "left",
        4: "active",
        5: "right",
        6: "lower left",
        7: "down",
        8: "lower right",
    }

    # We add decorations for the windows, and create the code-area subwindows
    subwindows = []
    for i in range(node_h * node_w):
        # We add the decorations
        window = windows[i + 1]
        window.border()
        top_descr = "This is the {} node".format(node_descs[i])
        window.move(0, 1 + int(third_w / 2) - int(len(top_descr) / 2))
        window.addstr(top_descr, curses.A_BOLD)
        window.scrollok(False)
        # We create the subwindow
        sub_h = quarter_h - 3
        sub_w = third_w - 3
        subwindow = window.derwin(sub_h, sub_w, 1, 1)
        subwindow.setscrreg(0, sub_h - 1)
        subwindow.scrollok(True)
        subwindows.append(subwindow)
    refresh()

    # We change print to enter our text into the console window, within our console

    def _print(*args):
        global _print_bfr

        start_point = (2, 1)
        _print_lines = cons_out_h - start_point[0]
        _print_cols = cons_out_w - start_point[1]
        windows["cons_out"].move(*start_point)
        output_str = " ".join(str(item) for item in args)
        output_str.replace("\n", "\n" + " " * start_point[1])
        _print_bfr += output_str + "\n" + " " * start_point[1]

        # We condition the print buffer so that no line exceeds the max line length,
        # and the number of lines is no longer than the max
        __print_bfr = ""
        __num_lines = 1
        _split_bfr = [item[:-1] for item in _print_bfr.split("\n")]

        for line in _split_bfr:
            while len(line) > _print_cols and __num_lines < _print_lines:
                __print_bfr += "\n" + " " * start_point[1] + line[:_print_cols]
                __num_lines +=1
            __print_bfr += "\n" + " " * start_point[1] + line[:_print_cols]
            __num_lines += 1

        __print_bfr = "\n".join(__print_bfr.split("\n")[-_print_lines:])
        windows["cons_out"].erase()
        windows["cons_out"].addstr(__print_bfr)
        windows["cons_out"].move(*start_point)
        refresh()

    def _input(prompt: str):


    # This is bad form but necessary
    print = _print

    # The step number we're at
    step_num = 0

    num_nodes = node_height * node_width

    # The grid of nodes
    node_grid = [[i + x for x in range(0, node_width)] for i in range(0, num_nodes, node_width)]

    print("Node grid shape is: {0} * {1}".format(node_height, node_width))

    # We print the node id grid
    for line in node_grid:
        print(", ".join(str(item) for item in line))

    # Our parsed code
    ast_root = tis_parser.parse(source)

    # We create the nodes
    machine = {n_id: TISNode(n_id, node_height, node_width, ast=val) for n_id, val in ast_root.nodes.items()}

    for n_id, node in machine.items():
        pass
        # TODO use this to add the code in the nodes
        # print("Node nr " + str(n_id) + ": " + str(node))

    print("Starting machine! ")
    result = input("Press ENTER to start stepping, F to go fast, S to go fast as fuck:")

    # Whether we should just skip asking for stepping
    fast_mode = result is "f"
    superfast_mode = result is "s"

    try:
        import time

        # We check whether we should go fast as fuck boiii
        if superfast_mode:
            while True:
                batch_num = 100000

                start = time.time()
                for i in range(batch_num):
                    for n_id, tis_node in machine.items():
                        tis_node.step(nodes=machine)

                step_num += batch_num

                print("10000 steps took:", round(1000 * (time.time() - start), 4), "ms, which means",
                      round(batch_num / (time.time() - start), 2), "Hz")
                print("Have now done {0} steps.".format(step_num))

        # We check whether we should go fast
        if fast_mode:
            # The main execution/stepping loop for asking for input
            while True:
                step_num += 1

                start = time.time()
                for n_id, tis_node in machine.items():
                    print("\nStepping node {0}.".format(n_id))

                    tis_node.step(nodes=machine)

                    # We print the accs for the node
                    print("Accs and baks in node {0}:".format(n_id), tis_node.accs, "|", tis_node.baks,
                          "\nCurrent acc and bak:", tis_node.accs[tis_node._register_cursor], "|",
                          tis_node.baks[tis_node._register_cursor])

                print("Step took:", round(1000 * (time.time() - start), 4), "ms, which means",
                      round(1 / (time.time() - start), 2), "Hz")
                print("Have now done {0} steps.".format(step_num))

        else:
            # The main execution/stepping loop for asking for input
            while True:
                step_num += 1

                start = time.time()
                for n_id, tis_node in machine.items():
                    print("\nStepping node {0}.".format(n_id))

                    tis_node.step(nodes=machine)

                    # We print the accs for the node
                    print("Accs and baks in node {0}:".format(n_id), tis_node.accs, "|", tis_node.baks,
                          "\nCurrent acc and bak:", tis_node.accs[tis_node._register_cursor], "|",
                          tis_node.baks[tis_node._register_cursor])

                print("Step took:", round(1000 * (time.time() - start), 4), "ms, which means",
                      round(1 / (time.time() - start), 2), "Hz")
                print("Have now done {0} steps.".format(step_num))
                resp = input("\nPress ENTER to step again, p to print all nodes:")
                # We check if we should print all nodes
                if resp.startswith("p"):
                    for n_id, node in machine.items():
                        print("Node nr " + str(n_id) + ":\n" + str(node))

    except (tis_helpers.ExecutionError, KeyboardInterrupt) as e:
        for n_id, node in machine.items():
            print("Node nr " + str(n_id) + ":\n" + str(node))

        print(str(e))
        print("Exiting.")


if __name__ == "__main__":
    # We get filename input
    while True:
        file_name = input("Please input a valid filename to use as source code.\n")

        try:
            with open(file_name, mode="r") as source_file:
                source = source_file.read()
            break
        except FileNotFoundError:
            print("File {0} could not be opened. Please try again.".format(file_name))

    # We start the execution, and we use ncurses
    print("Ok! Starting execution!\n")

    # This is the string which keeps the currently printed data
    _print_bfr = ""
    curses.wrapper(partial(run_src, source, 4, 5))
