# synopsis.py

Small script to speed-copy some subset of files from a project into an into an
LLM, and to quickly edit what's included in the subset.

I tried Cursor for about half an hour earlier this afternoon, and I'm pretty
unimpressed compared to what's achievable by just copy-pasting entire files
into a chat prompt. I wrote this to accelerate that process a bit.

## Installation
```sh
# clone the repo
git clone https://github.com/FraserLee/synopsis

# make the script executable
cd synopsis
chmod +x synopsis.py

# Add an alias to the script. For the default shell on macos:
echo "alias synopsis='$(pwd)/synopsis.py'" >> ~/.zshenv
source ~/.zshenv
```

## Usage

```sh
synopsis # copy every files listed in `.llm_info`, wrapped in code blocks, to
         # the clipboard.

synopsis --edit # interactively add and remove files from `.llm_info`
```

## Possible Future Plans

It might be worthwhile to query to some weaker model to summarize files that
are too long to copy in full, pulling out externally visible functions and
types, and any important context. Then again, context windows are pretty long
these days, so a complete project dump might be fine for everything I'm looking
to do, too.
