# Changelog

Newest first. Version numbers are in `scripts/rtlmd.py` (`--version`) and in the title of `SKILL.md`.

## Unreleased
- Repository files for publishing: English `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, issue template, CI workflow, MIT license.
- Wording made vendor-neutral and free of references to one person's setup; no behaviour change.
- `scripts/test_rtlmd.py` now writes direction characters as escapes instead of literal invisible characters.

## 2.2.0 (2026-11-15): errors and contradictions found in a review of 2.1.0
Fixed:
- A plain indented line (for example the continuation of a list item) got its direction characters placed before its indentation, so it lost the indentation and cut the list. Indentation is now kept in front of them.
- File and identifier names with underscores (`my_file_name`) were split into spans joined by bare underscores, which could not be fixed stably and was left untouched. They are now one span with escaped underscores.
- Products such as `5*3*2` could not be fixed stably for the same reason. They now are.
- `SKILL.md` contradicted the script in three places (HTML tags "left exactly as written" while emphasis tags are removed; "a line with no Arabic is left alone" while its bold markup is removed; "a table in a quote is only reported"). All corrected.
- 13 of the 21 check codes were not documented. There is now a "Check codes" section, and a test fails if a code is ever added without it.

Added:
- Italics (`*x*`, `_x_`) are removed like bold, by the same rule, never inside code, math, links, wikilinks or comments.
- Four-space indented code after a blank line (outside lists) is recognized and left untouched.
- A table inside a quote or callout is converted to a list, with the quote marks kept.
- Tests: 34 in total, including the documentation check, plus fuzz pieces for italics, underscores and asterisks.

## 2.1.0 (2026-11-15): bold is abandoned completely
- Reason: bold did not render in the author's Obsidian notes even as `<b>` tags, so every form of bold is dropped.
- `fix` now removes `**x**`, `***x***`, `<b>`, `<i>`, `<strong>` and `<em>` and keeps the text, instead of converting to `<b>`. It does this on lines without Arabic too. Code, math, link targets and URLs are untouched.
- `check` reports `bold-markup-not-wanted` for any bold marker or emphasis tag left (the old code `asterisk-bold-use-b-tag` is gone).
- `SKILL.md`: the bold rule now says never to write emphasis and to use structure instead.
- The `fix -o OUT` messages name the output file instead of the source file.

## 2.0.1 (2026-11-15): two gaps found by a second round of probing
- Numbers with a thousands separator or an exponent (`1,000`, `1.5e3`) were split into several spans, and `1.5e3` was not stable on a second run. Each is now one span.
- Two lone dollars in the price shape `5$ ... 6$` were read as a single fake equation and rewritten. Such a line is now left untouched and reported as `unbalanced-dollar`.
- Safety net: `fix` rewrites a line only when the result is stable on a second pass and passes the structural checks. Otherwise the line is kept exactly as it was and `check` reports it. Found with 30000 random lines of mixed syntax, where about 0.3% were unfixable shapes (stray `$`, `5$`).
- Tests: new golden cases, must-flag cases and a safety-net test (29 in total).

## 2.0.0 (2026-11-14): full hardening release

Fixed, found by testing 1.x against real Markdown:
- Ordered lists (`1.` / `1)`) were rewritten as `$1$.` and stopped being lists. Markers now stay outside the wrapper.
- Task boxes (`- [ ]`, `- [x]`), callouts (`> [!note]`, `> [!faq]-`), footnote definitions and quote nesting were mangled. They are now block markers.
- Wikilinks, embeds, tags, block ids, footnote references, comments, HTML entities and images had their digits and letters turned into math. They are now left untouched.
- Table rows were wrapped and filled with math instead of being left alone. Tables are now converted to lists.
- `$$...$$` inside a sentence and `\$` prices produced broken, non-idempotent output. Inline `$$` becomes inline math, `\$5` becomes `$\$5$`, touching spans get a space, and an unpaired `$` is reported instead of being rewritten.
- Math that contains commands (`\frac{a}{b}`, `\vec{F}`, `\Phi_m`) kept italic Latin letters, and display math was never normalized. Both are now upright, with subscripts braced (`_{\mathrm{m}}`).
- Trailing hard line breaks (two spaces) were removed, and CRLF line endings and the BOM were silently changed. All three are preserved now.
- Fences using `~~~` or four backticks, and fences or `$$` inside quotes and callouts, were not recognized.
- Directory arguments did not exist; a folder is now processed by content (UTF-8 text with Arabic), not by extension.

Added:
- `check`: key bullet format, plain list right after a key, Greek letters missing from a key, long key definitions, `\hline` and unbalanced braces in display math, unpaired `$`, unclosed `$$`, direction characters in display math, and worked-solution structure (missing sections, order, steps, final summary).
- `fix --diff` (preview, writes nothing), `--keep-tables`, `--keep-rules`.
- `scaffold N`: an empty worked-solution skeleton.
- `scripts/test_rtlmd.py`: 28 tests, 4000 random lines and 1500 random documents for idempotency.
- `assets/example_obsidian_*.md`, `--version`, this file.
- Files are written atomically and only when something changed.
- Horizontal rules are removed by `fix` (front matter and heading underlines are kept).
- The differential `d` (and `dt` when `t` is in the key) no longer needs a key.

Behaviour that did not change: plain Arabic lines with inline math, digits and Latin words give the same output as 1.2 (compared line by line against 1.2 on a sample, and kept as golden cases in the tests).

## 1.2 (2026-11-14): bold fix (dropped in 2.1.0)
- `**x**` and `***x***` are converted to `<b>x</b>` and `<b><i>x</i></b>`, because asterisk emphasis does not render next to the direction characters. `check` flags leftover `**`.

## 1.1 (2026-11-12): rebuilt
- Per-equation key (`المفتاح:`) replaced the symbol list at the top of the file.
- Worked-solution structure, SKILL.md and script rewritten; test cases added.

## 1.0: first version
- Direction rules (LRI/PDI around math, RLM+RLI+PDI around Arabic lines), Latin and digits as LaTeX, edge-operator rule, Arabic-Indic digits banned, `fix` and `check`.
