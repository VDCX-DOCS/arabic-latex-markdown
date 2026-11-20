# arabic-latex-markdown

[![test](https://github.com/VDCX-DOCS/arabic-latex-markdown/actions/workflows/test.yml/badge.svg)](https://github.com/VDCX-DOCS/arabic-latex-markdown/actions/workflows/test.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Make Arabic Markdown that contains LaTeX math, Latin words and digits render correctly in right-to-left editors such as Obsidian. Brackets stop flipping, an `=` sign stops jumping to the wrong side, and numbered lists stop breaking.

It ships in two parts that work together:

- `scripts/rtlmd.py`: a command-line tool with no dependencies (Python 3.9 or newer) that fixes and checks files.
- `SKILL.md`: the written rules and the reasons behind them. Any person, or any AI model or agent that can read files and run a command, can follow it. It is not tied to one vendor.

## The problem

In an RTL editor, Latin letters, digits, brackets and operators are "weak" or left-to-right characters. Next to Arabic they get reordered, so a bracket lands on the wrong side, `S =` renders with its sign on the other side, and a line that starts with an English letter is laid out left-to-right and drags the Arabic sentence after it. The fix is a fixed set of rules: wrap every math span and every Arabic line in Unicode direction isolates, write every Latin letter and digit as LaTeX, and keep operators and brackets outside the math at the edges. The tool applies those rules for you. The full list, with the reason for each rule, is in [`SKILL.md`](SKILL.md).

## Quick start

```bash
git clone https://github.com/VDCX-DOCS/arabic-latex-markdown.git
cd arabic-latex-markdown

python scripts/rtlmd.py fix   path/to/notes        # rewrite a file or a whole folder in place
python scripts/rtlmd.py check path/to/notes        # report what is still wrong
```

- `fix PATH`: rewrites in place. Only touches files that change. Running it twice changes nothing.
- `fix PATH --diff`: shows what would change and writes nothing.
- `fix PATH -o OUT`: writes the result of one file to `OUT`.
- `check PATH`: lists problems and exits with code 1 if there are any (`--strict` also fails on warnings).
- `scaffold N`: prints an empty skeleton for `N` worked-solution questions.
- `--version`: prints the version.

A folder is searched by content, not by extension: any UTF-8 text file that contains Arabic is processed. Folders whose names start with a dot are skipped. Line endings and a byte-order mark are preserved.

`fix` never guesses. A line is rewritten only when the result is stable on a second pass. A line that cannot be fixed safely is left exactly as it was and `check` reports it, so always read the `check` output after `fix`.

## What it does

- Wraps each inline math span in LRI and PDI, and each Arabic line in RLM, RLI and PDI, placed after any list, quote or heading marker.
- Turns bare Latin letters and digits inside Arabic text into LaTeX, and writes Latin symbols upright with `\mathrm{...}`.
- Moves operators and brackets at the edge of a math span out of it, next to the Arabic.
- Replaces Arabic-Indic digits with `0-9`.
- Removes bold and italic markup, converts tables to lists and removes decorative horizontal rules (each can be switched off with `--keep-tables` and `--keep-rules`).
- Leaves code, front matter, URLs and Obsidian syntax (wikilinks, embeds, tags, comments) alone.
- `check` also verifies display math and the small symbol key after each equation, and checks the structure of worked solutions.

See [`assets/`](assets) for before and after pairs. The direction characters are invisible in those files, which is the point.

## Using it with an AI model or agent

The rules live in plain Markdown and the tool is a single script, so nothing here depends on a particular model. Give the agent the repository (or just `SKILL.md` and the `scripts` folder) and tell it to follow `SKILL.md`: write the file, run `fix`, then `check`, and repair every reported problem. [`AGENTS.md`](AGENTS.md) holds the same instruction in the short form that coding agents look for by convention. Tools that load skills from a folder containing a `SKILL.md` can use this directory as is.

## Development

```bash
python scripts/test_rtlmd.py
```

The suite has 34 tests, including random-input checks that `fix` is idempotent, and it fails if a check code is added without being documented in `SKILL.md`. After changing an example file, regenerate it with `fix` rather than editing it by hand. CI runs the tests on Python 3.9 and 3.12 and verifies that the example pairs are still in sync. See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CHANGELOG.md`](CHANGELOG.md).

## Known limits

- Emphasis is detected in pairs. A lone `*` or `_` is left alone, and a pair of literal ones is read as italics unless escaped with a backslash.
- Code is recognized when fenced, or indented by four spaces after a blank line outside a list.
- The tool cannot see your editor. If a new kind of line misbehaves, open an issue with the rendered result.

## License

[MIT](LICENSE)
