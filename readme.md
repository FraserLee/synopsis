# synopsis.py

Small script to speed-copy some subset of files from a project into an into an
LLM, and to quickly edit what's included in the subset.

![1](https://raw.githubusercontent.com/FraserLee/readme_resources/main/screenshot%204.png)

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

The clipboard output is formatted as
```markdown
\`\`\`
file 1 path
\`\`\`
\`\`\`
file 1 contents
\`\`\`

\`\`\`
file 2 path
\`\`\`
\`\`\`
file 2 contents
\`\`\`

etc.
```

## Possible Future Plans

**Project motivation:** I tried Cursor for about half an hour earlier this
afternoon, and I'm pretty unimpressed compared to what's achievable by just
copy-pasting entire files into a chat prompt. I only wrote this to accelerate
that process a bit, so plans for the future are pretty limited.

That said, it might be worthwhile to query to some weaker model to summarize
files that are too long to copy in full, pulling out externally visible
functions and types, and any important context. Then again, context windows are
pretty long these days, so a complete project dump might be fine for everything
I'm looking to do, too.
