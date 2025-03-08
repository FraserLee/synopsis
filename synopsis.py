#!/usr/bin/env -S uv run --script
# /// script
# requires-python = "~=3.13"
# dependencies = [
# "pyperclip==1.9.0",
# ]
# ///

import os
import sys
import argparse
import curses
import pyperclip
from typing import Optional

# ----------------------- build a copy of the filesystem -----------------------

class Node:
    name: str
    path: str
    parent: Optional["Dir"]
    selected: bool = False # is included in .llm_info

    def __init__(self, name, path, parent):
        self.name = name
        self.path = path
        self.parent = parent

class Dir(Node):
    expanded: bool = False

    def __init__(self, name, path, parent=None):
        super().__init__(name, path, parent)

        self.children = []

        for child in os.listdir(os.path.join(os.getcwd(), path)):
            full_path = os.path.join(path, child)
            self.children.append(Dir(child, full_path, self) if os.path.isdir(full_path) else Node(child, full_path, self))

        # directories first, then files - each alphabetically
        self.children.sort(key=lambda x: (not isinstance(x, Dir), x.name))


# ------------------------ display selector with curses ------------------------

def get_visible_nodes(node, depth=0):
    visible = [(node, depth)]
    # If directory is expanded, recurse on children
    if isinstance(node, Dir) and node.expanded:
        for child in node.children:
            visible.extend(get_visible_nodes(child, depth + 1))
    return visible

def interactive_selector(stdscr, root) -> list[str]:

    curses.curs_set(0)
    stdscr.nodelay(False)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)  # selected
    curses.init_pair(2, curses.COLOR_RED, -1)    # not selected

    current_index = 0
    window_pos = 0

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        header = ("Use ↑/↓ or j/k to navigate, "
                  "←/h to collapse, →/l to expand, "
                  "SPACE to toggle, ENTER to finish, q to quit.")
        stdscr.addstr(0, 0, header[:width-1])

        visible_list = get_visible_nodes(root, -1)[1:]  # Skip the root node

        for i in range(window_pos, min(len(visible_list), window_pos + height - 1)):
            node, depth = visible_list[i]

            display_name = node.name
            if isinstance(node, Dir):
                if node.expanded:  display_name = "📂 " + display_name
                else:              display_name = "📁 " + display_name
            else:
                display_name = {
                    "py": "🐍 ", "rs": "🦀 ", "md": "📝 ", "txt": "📝 ", "sh":
                    "🐚 ", "java": "☕️ "
                }.get(node.name.split(".")[-1], "📄 ") + display_name

            display_name = ("    " * depth) + display_name

            colour = curses.color_pair(1) if node.selected else curses.color_pair(2)
            if i == current_index:
                stdscr.addstr(i - window_pos + 1, 0, display_name[:width-1], colour | curses.A_REVERSE)
            else:
                stdscr.addstr(i - window_pos + 1, 0, display_name[:width-1], colour)

        stdscr.refresh()

        key = stdscr.getch()
        if key in (curses.KEY_UP, ord('k')):
            if current_index > 0:
                current_index -= 1
                window_pos = max(0, min(window_pos, current_index - 3))

        elif key in (curses.KEY_DOWN, ord('j')):
            if current_index < len(visible_list) - 1:
                current_index += 1
                window_pos = max(0, max(window_pos, current_index - height + 5))

        elif key in (curses.KEY_LEFT, ord('h')):
            node, _ = visible_list[current_index]
            if isinstance(node, Dir) and node.expanded:
                node.expanded = False
            elif node.parent and node.parent.parent:
                node.parent.expanded = False
                current_index = 0
                for i, (n, _) in enumerate(visible_list):
                    if n == node.parent:
                        current_index = i
                        break

        elif key in (curses.KEY_RIGHT, ord('l')):
            node, _ = visible_list[current_index]
            if isinstance(node, Dir) and not node.expanded:
                node.expanded = True
            else:
                pass

        elif key == ord(' '):
            node, _ = visible_list[current_index]
            node.selected = not node.selected

        elif key == ord('q'):
            sys.exit(0)

        elif key in (curses.KEY_ENTER, 10, 13):
            break

    def collect_selected(node: Node) -> list[str]:

        if isinstance(node, Dir):
            subpaths = [collect_selected(child) for child in node.children]
            return [path for subpath in subpaths for path in subpath]

        else:
            return [node.path] if node.selected else []

    return collect_selected(root)

# ----------------------------------- cli app ----------------------------------

parser = argparse.ArgumentParser(description="Quickly copy relevant parts of a file tree to clipboard to paste into an LLM.")
parser.add_argument("--edit", action="store_true", help="Edit .llm_info file")
args = parser.parse_args()

llm_info_path = ".llm_info"
directory = os.getcwd()
root = Dir(name=os.path.basename(directory), path="")
root.expanded = True

# If .llm_info does not exist or --edit is specified, run interactive selection.
if args.edit or not os.path.exists(llm_info_path):
    selected_files = curses.wrapper(lambda stdscr: interactive_selector(stdscr, root))
    # Save the selected file paths.
    try:
        with open(llm_info_path, "w", encoding="utf-8") as f:
            for path in selected_files:
                f.write(path + "\n")
    except Exception as e:
        print(f"Error writing {llm_info_path}: {e}")
        sys.exit(1)
else:
    # Otherwise, read the .llm_info file for previously selected files.
    try:
        with open(llm_info_path, "r", encoding="utf-8") as f:
            selected_files = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading {llm_info_path}: {e}")
        sys.exit(1)

# Build the output from the selected file paths.
output = []
for path in selected_files:
    full_path = os.path.join(directory, path)
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        content = f"[Error reading file: {e}]"
    output.append(f"```\n{path.strip()}\n```")
    output.append(f"```\n{content.strip()}\n```")
    output.append("")

output_text = "\n".join(output)

print(output_text)

# output to clipboard
try:
    pyperclip.copy(output_text)
    print("Output copied to clipboard.")
except Exception as e:
    print(f"Failed to copy to clipboard: {e}")
