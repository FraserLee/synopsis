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

def get_all_files(directory):
    """
    Recursively collects all file paths under the given directory.
    Returns paths relative to the provided directory.
    """
    files = []
    for root, dirs, filenames in os.walk(directory):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, directory)
            files.append(rel_path)
    return sorted(files)

def interactive_selector(stdscr, file_list):
    """
    Displays an interactive tree view using curses.
    - Arrow keys move the selection.
    - Space toggles inclusion (green = included, red = excluded).
    - Enter finishes selection.
    Returns the list of file paths that are selected.
    """
    # No files are selected by default.
    selections = [False] * len(file_list)
    current_index = 0

    # Curses setup.
    curses.curs_set(0)
    stdscr.nodelay(False)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)  # Included files
    curses.init_pair(2, curses.COLOR_RED, -1)    # Excluded files

    window_pos = 0
    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        header = "Use ↑/↓ or j/k to navigate, SPACE to toggle, ENTER to finish, q to quit. (Green = included, Red = excluded)"
        stdscr.addstr(0, 0, header[:width-1])

        # Display files list, starting from window_pos.
        for idx, path in enumerate(file_list):
            if idx < window_pos: continue
            if idx >= window_pos + height - 1: break
            color = curses.color_pair(1) if selections[idx] else curses.color_pair(2)
            # Highlight the current selection.
            if idx == current_index:
                stdscr.addstr(idx+1-window_pos, 0, path[:width-1], color | curses.A_REVERSE)
            else:
                stdscr.addstr(idx+1-window_pos, 0, path[:width-1], color)
        stdscr.refresh()

        key = stdscr.getch()
        if key in (curses.KEY_UP, ord('k')) and current_index > 0:
            current_index -= 1
            window_pos = max(0, min(window_pos, current_index - 3))
        elif key in (curses.KEY_DOWN, ord('j')) and current_index < len(file_list) - 1:
            current_index += 1
            window_pos = max(0, max(window_pos, current_index - height + 5))
        elif key == ord(' '):
            selections[current_index] = not selections[current_index]
        elif key == ord('q'):
            sys.exit(0)
        elif key in (curses.KEY_ENTER, 10, 13):
            break

    # Return only the file paths that remain selected.
    return [file_list[i] for i in range(len(file_list)) if selections[i]]


# ----------------------------------- cli app ----------------------------------

parser = argparse.ArgumentParser(description="Quickly copy relevant parts of a file tree to clipboard to paste into an LLM.")
parser.add_argument("--edit", action="store_true", help="Edit .llm_info file")
args = parser.parse_args()

llm_info_path = ".llm_info"
directory = os.getcwd()
file_list = get_all_files(directory)

# If .llm_info does not exist or --edit is specified, run interactive selection.
if args.edit or not os.path.exists(llm_info_path):
    # Wrap the interactive_selector with curses.
    selected_files = curses.wrapper(lambda stdscr: interactive_selector(stdscr, file_list))
    # Save the selected file paths.
    try:
        with open(llm_info_path, "w", encoding="utf-8") as f:
            for path in selected_files:
                f.write(path + "\n")
    except Exception as e:
        print(f"Error writing {llm_info_path}: {e}")
        sys.exit(1)
else:
    # Read the .llm_info file.
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

# output to the clipboard.
try:
    pyperclip.copy(output_text)
    print("Output copied to clipboard.")
except Exception as e:
    print(f"Failed to copy to clipboard: {e}")
