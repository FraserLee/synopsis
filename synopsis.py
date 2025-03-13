#!/usr/bin/env python3

import os
import sys
import argparse
import platform
import subprocess
from typing import Dict, Optional, Set

try:
    import curses
except ImportError:
    print("This script requires the curses module.")
    print("On Windows, there's some ways to go about installing it, but it's not there by default.")
    sys.exit(1)

selected_files: Set[str] = set()

# ----------------------- build a copy of the filesystem -----------------------

class Node:
    name: str
    path: str
    parent: Optional["Dir"]
    selected: bool # is included in .llm_info

    def __init__(self, name, path, parent):
        self.name = name
        self.path = path
        self.parent = parent
        self.selected = path in selected_files

class Dir(Node):
    expanded: bool

    def __init__(self, name, path, parent):
        super().__init__(name, path, parent)

        self.children = []

        for child in os.listdir(os.path.join(os.getcwd(), path)):
            full_path = os.path.join(path, child)
            if os.path.isdir(full_path):
                self.children.append(Dir(child, full_path, self))
            else:
                self.children.append(Node(child, full_path, self))

        # directories first, then files - each alphabetically
        self.children.sort(key=lambda x: (not isinstance(x, Dir), x.name))

        self.selected = all(child.selected for child in self.children)
        self.expanded = any(
            child.selected or (isinstance(child, Dir) and child.expanded)
            for child in self.children
        )
        self.selected = self.selected and len(self.children) > 0
        self.expanded = self.expanded and len(self.children) > 0



# ------------------------ display selector with curses ------------------------

def get_visible_nodes(node, depth=0):
    visible = [(node, depth)]
    # If directory is expanded, recurse on children
    if isinstance(node, Dir) and node.expanded:
        for child in node.children:
            visible.extend(get_visible_nodes(child, depth + 1))
    return visible

def invert(node, direction=None):
    if direction is not None:
        node.selected = direction
    else:
        node.selected = not node.selected
    if isinstance(node, Dir):
        for child in node.children:
            invert(child, node.selected)

def interactive_selector(stdscr, root) -> Set[str]:

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

        header = [
            "Use ↑/↓ or j/k to navigate, ←/h to collapse, →/l to expand,",
            "SPACE to toggle, ENTER to finish, q to quit."
        ]
        for i, line in enumerate(header):
            stdscr.addstr(i, 0, line[:width-1])


        visible_list = get_visible_nodes(root, -1)[1:]  # Skip the root node

        for i in range(window_pos, min(len(visible_list), window_pos + height - len(header))):
            node, depth = visible_list[i]

            display_name = node.name
            if isinstance(node, Dir):
                if node.expanded:  display_name = "📂 " + display_name
                else:              display_name = "📁 " + display_name
            else:
                ext = node.name.split(".")[-1]
                icon = {
                    "py": "🐍 ",
                    "rs": "🦀 ",
                    "md": "📝 ",
                    "txt": "📝 ",
                    "sh": "🐚 ",
                    "java": "☕️ "
                }.get(ext, "📄 ")
                display_name = icon + display_name

            display_name = ("    " * depth) + display_name

            colour = curses.color_pair(1) if node.selected else curses.color_pair(2)
            if i == current_index:
                stdscr.addstr(i - window_pos + len(header), 0, display_name[:width-1], colour | curses.A_REVERSE)
            else:
                stdscr.addstr(i - window_pos + len(header), 0, display_name[:width-1], colour)


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

        elif key == ord(' '):
            node, _ = visible_list[current_index]
            invert(node)

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

    return set(collect_selected(root))

# ----------------------------------- cli app ----------------------------------

parser = argparse.ArgumentParser(
    description="Quickly copy relevant parts of a file tree to clipboard to paste into an LLM."
)
parser.add_argument("--edit", action="store_true", help="Edit .llm_info file")
parser.add_argument("--tag", action="store_true", help="Wrap output in <project> tag")
args = parser.parse_args()

llm_info_path = ".llm_info"
directory = os.getcwd()

# First, read the .llm_info file
if os.path.exists(llm_info_path):
    try:
        with open(llm_info_path, "r", encoding="utf-8") as f:
            selected_files = set(line.strip() for line in f if line.strip())
    except Exception as e:
        print(f"Error reading {llm_info_path}: {e}")
        sys.exit(1)

# If .llm_info does not exist, or is empty, or --edit is specified - run interactive selection.
if len(selected_files) == 0 or args.edit:

    root = Dir(os.path.basename(directory), "", None)
    root.expanded = True

    selected_files = curses.wrapper(lambda stdscr: interactive_selector(stdscr, root))
    # Save the selected file paths.
    try:
        with open(llm_info_path, "w", encoding="utf-8") as f:
            for path in sorted(selected_files):
                f.write(path + "\n")
    except Exception as e:
        print(f"Error writing {llm_info_path}: {e}")
        sys.exit(1)

# ---------------------------- git project structure ---------------------------

project_structure = None
try:
    # Check if we're inside a git repository
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True, text=True, check=True
    )
    if result.stdout.strip() == "true":
        # Check if tree is installed
        try:
            subprocess.run(["tree", "--version"], capture_output=True, text=True, check=True)
            tree_installed = True
        except Exception:
            tree_installed = False

        if tree_installed:
            # Use git ls-files piped to tree --fromfile
            git_files = subprocess.run(
                ["git", "ls-files"],
                capture_output=True, text=True, check=True
            )
            tree_result = subprocess.run(
                ["tree", "--fromfile"],
                input=git_files.stdout, text=True, capture_output=True, check=True
            )
            project_structure = tree_result.stdout.strip()
        else:
            # Fallback: just list the tracked files
            git_files = subprocess.run(
                ["git", "ls-files"],
                capture_output=True, text=True, check=True
            )
            project_structure = git_files.stdout.strip()
except Exception:
    project_structure = None

# ----------------------------- build final output -----------------------------

_SPECIAL_FILENAMES: Dict[str, str] = {
    ".bash_profile": "bash",
    ".bashrc": "bash",
    ".zshrc": "bash",
    "berksfile": "ruby",
    "cmakelists.txt": "cmake",
    "dockerfile": "dockerfile",
    "gemfile": "ruby",
    "makefile": "makefile",
    "procfile": "yaml",
    "vagrantfile": "ruby",
}

_LANGUAGE_MAP: Dict[str, str] = {
    "bat": "bat",
    "cfg": "ini",
    "clj": "clojure",
    "cljs": "clojure",
    "coffee": "coffeescript",
    "conf": "ini",
    "cs": "csharp",
    "csx": "csharp",
    "erb": "ruby",
    "erl": "erlang",
    "ex": "elixir",
    "exs": "elixir",
    "f90": "fortran",
    "f95": "fortran",
    "groovy": "groovy",
    "h": "c",
    "hbs": "handlebars",
    "hpp": "cpp",
    "hs": "haskell",
    "ino": "cpp",
    "jl": "julia",
    "js": "javascript",
    "kt": "kotlin",
    "kts": "kotlin",
    "log": "",
    "md": "markdown",
    "mjs": "javascript",
    "mm": "objective-c++",
    "pl": "perl",
    "pm": "perl",
    "ps1": "powershell",
    "psm1": "powershell",
    "py": "python",
    "pyi": "python",
    "pyw": "python",
    "rb": "ruby",
    "rs": "rust",
    "sh": "bash",
    "sv": "systemverilog",
    "svh": "systemverilog",
    "tex": "latex",
    "ts": "typescript",
    "txt": "",
    "v": "verilog",
    "vhd": "vhdl",
    "zsh": "bash",
}

def get_language_hint(filename: str) -> str:
    """Return a language hint for syntax highlighting based on the filename.

    The logic works as follows:
    - Special cases are handled using `_SPECIAL_FILENAMES`.
      E.g. "CMakeLists.txt" -> "cmake".
    - Standard extensions are mapped using `_LANGUAGE_MAP`.
      E.g. "py" -> "python".
    - The rest are mapped to their extension.
      E.g. "foo.bar" -> "bar".

    Args:
        filename: Input filename to analyze, can include path components

    Returns:
        Language identifier string compatible with common syntax highlighters,
        or empty string if no appropriate mapping exists.
    """
    # Check special filenames first
    basename = os.path.basename(filename.lower())
    if basename in _SPECIAL_FILENAMES:
        return _SPECIAL_FILENAMES[basename]

    # Handle standard extensions
    _, ext = os.path.splitext(filename.lower())
    extension = ext.lstrip('.')
    return _LANGUAGE_MAP.get(extension, extension)

output_lines = []
if args.tag:
    output_lines.append("<project>")
if project_structure:
    output_lines.append("Project structure:")
    output_lines.append("```")
    output_lines.append(project_structure)
    output_lines.append("```")
    output_lines.append("")  # blank line

output_lines.append("Relevant files:")
for path in sorted(selected_files):
    full_path = os.path.join(directory, path)
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
            content = content.replace("\r\n", "\n")
            content = ('\n' + content).replace("\n```", "\n\\`\\`\\`").strip()
    except Exception as e:
        content = f"[Error reading file: {e}]"

    # Get language hint based on file extension
    lang_hint = get_language_hint(path)

    output_lines.append(f"\n{path}")
    output_lines.append(f"```{lang_hint}\n{content}\n```")
    output_lines.append("")

if args.tag:
    output_lines.append("</project>")

output_text = "\n".join(output_lines)

print(output_text)

# output to clipboard
try:
    system = platform.system()
    if system == "Darwin":
        subprocess.run("pbcopy", universal_newlines=True, input=output_text)
    elif system == "Linux":
        subprocess.run("xclip -selection clipboard", shell=True, universal_newlines=True, input=output_text)
    elif system == "Windows":
        subprocess.run("clip", universal_newlines=True, input=output_text)
    else:
        raise NotImplementedError(f"Unsupported OS: {system}")

    print("Offering to inscrutable machine-gods copied to clipboard 🌌")

except Exception as e:
    print(f"Failed to copy to clipboard: {e}")

