---
name: arabic-latex-markdown
description: Write, edit, convert or repair Markdown files whose prose is Arabic and that contain LaTeX math, English words, symbols or digits (science and math lessons, grammar notes, worked solutions, exam answers, study sheets). Makes direction, brackets, operators, numbered lists and Obsidian syntax render correctly in an RTL editor such as Obsidian, and puts a small key after every equation. Use this whenever the user asks for Arabic notes, solutions or summaries with equations, mentions RTL, bidi, flipped brackets, a wrong "=" position, bold that does not render, a broken numbered list, a sentence that starts with an English letter and runs left-to-right, or asks to fix or convert an Arabic .md file or a whole folder of notes, even if they never mention LaTeX handling explicitly.
---

# Arabic Markdown with LaTeX that does not break (v2.2.0)

## Why this skill exists

In an RTL editor (the rules below were developed and verified in Obsidian), Latin letters, digits, brackets and operators are "weak" or left-to-right characters. Next to Arabic they get reordered: a bracket flips or lands on the wrong side, `S =` renders with the sign jumping to the other side, and a line that starts with an English letter is laid out left-to-right and wrecks the Arabic sentence after it. The author fought this for a long time and found a set of rules that works in that editor. They are verified, so treat them as a spec, not as suggestions. If one seems wrong, ask the person you are working for to test a change in their editor first. These instructions are written for any assistant or person; nothing in them depends on a particular model or product.

## Workflow

1. Write ordinary Markdown: Arabic prose, inline math between single dollar signs, display math between double dollar signs on their own lines, and a key after each display equation. Do not type the invisible direction characters by hand, and do not type `**` for bold (see the rules); the script handles both.
2. Run `python scripts/rtlmd.py fix PATH`. PATH is a file or a folder. It rewrites in place (or `-o OUT` for one file), only touches a file when something changed, and keeps its line endings and BOM. It is idempotent, so running it twice changes nothing the second time. `--diff` shows what would change and writes nothing.
3. Run `python scripts/rtlmd.py check PATH`. Fix every failure (✘) by hand, then check again. Read every warning (⚠) and fix it too, unless the symbol is a unit or a plain function.
4. Recompute every number in code before delivering. Deliver only when the check passes and each result is confirmed.
5. After changing anything in `scripts/rtlmd.py`, run `python scripts/test_rtlmd.py`. It must print one ✔ line.

Starting a new set of solved problems: `python scripts/rtlmd.py scaffold N` prints an empty skeleton for N questions with the sections in the right order. Fill it in, then run `fix`.

A folder is searched by content, not by extension: any UTF-8 text file containing Arabic is processed. Folders whose names start with a dot (`.obsidian`, `.git`) are skipped.

## The direction rules, and the reason for each

- **All Latin letters and all digits inside Arabic text are LaTeX**, whatever they are: section numbers, question numbers, names like DNA, plain counts, and the letters that label points (`$\mathrm{A}$`). Latin text written as math is treated by the editor as one isolated unit, so it cannot drag the neighbouring Arabic around. Exceptions: URLs, file names, code, front matter, and Obsidian syntax (below). A line with no Arabic and no math is left alone, except that bold and italic markup is still removed from it. A file or identifier name that contains an underscore (`my_file_name`) becomes one span with escaped underscores (`$\mathrm{my\_file\_name}$`), because a bare underscore would turn into a subscript.
- **Latin symbols inside LaTeX use `\mathrm{...}`** so they are upright, not italic. This holds for every math span, including ones that contain commands: `\frac{a}{b}` becomes `\frac{\mathrm{a}}{\mathrm{b}}`, and a subscript word goes upright inside braces, for example `\Phi_{\mathrm{m}}`. Greek letters, other commands, `\text{...}` and environment names stay as they are. It also holds inside display math.
- **A number is one span**: `1,000`, `12,5`, `3.5` and `1.5e3` each stay in a single LaTeX span.
- **Digits are always 0-9.** Arabic-Indic digits are banned in every Markdown file, display math included; this is a deliberate house rule.
- **No bold and no italic, at all.** In the verified Obsidian setup neither `**text**` nor `<b>text</b>` renders next to the direction characters, so the skill never writes emphasis markup. Make a point stand out with structure instead: a heading, its own line, a list item, or a short lead-in sentence such as `ملاحظة:`. `fix` removes `**`, `***`, `*text*`, `_text_`, `<b>`, `<i>`, `<strong>` and `<em>` and keeps the text (code, math, link targets, wikilinks, comments and URLs are skipped), and `check` reports `bold-markup-not-wanted` for anything left over, for example `** text **` with spaces inside. A literal asterisk or underscore that comes in a pair would be read as italics, so escape it with a backslash. Do not write the key label (`المفتاح:`) or any other label as bold.
- **Each inline math span is wrapped in LRI (U+2066) before and PDI (U+2069) after.** This isolates the left-to-right run from the Arabic around it, which is what stops brackets and order from flipping.
- **Each Arabic line is wrapped as RLM (U+200F) + RLI (U+2067) + content + PDI (U+2069)**, placed after any block marker. Editors choose a line's direction from its first strong character outside isolates. Without the RLM, a line that starts with Latin or with math is laid out left-to-right. With RLM plus RLI, the line is right-to-left whatever it starts with.
- **Block markers stay outside the wrapper and are never turned into math**: bullets, ordered-list numbers (`1.` and `1)`), task boxes (`- [ ]`, `- [x]`), quote marks, callout headers (`> [!note]`, `> [!faq]-`), heading hashes and footnote definitions (`[^1]:`). A heading's own number, as in `## 1. اختبار`, is part of its text and becomes `$1$`.
- **Obsidian syntax is left exactly as written**: wikilinks and embeds (`[[...]]`, `![[...]]`), images, tags (`#tag`), block ids (`^abc`), footnote references (`[^1]`), `<!-- -->` and `%% %%` comments, HTML tags and entities (except the bold and italic tags removed by the emphasis rule below). A line made only of these is not wrapped. Four-space indented code (after a blank line, outside a list) is left untouched like fenced code, and an indented line that continues a list item keeps its indentation.
- **Operators at the edge of a math span move out of LaTeX** when they sit next to Arabic: write `الملح $\mathrm{S}$ = الماء`, never `$\mathrm{S =}$`. This applies to `=`, `+`, `−`, `<`, `>`, `→` and the like. An operator between two symbols or two numbers stays inside: `$23 + 23 = 46$`, `$\mathrm{S_{out} > S_{in}}$`. If the sign stays inside the math next to Arabic, the editor flips it to the wrong side. Keep the author's own wording: when the source says `الناتج = 4`, the result is `الناتج = $4$` (sign untouched, only the number becomes LaTeX). Never swap the sign for a colon or any other punctuation, and never add or drop words to make a rule fit.
- **Brackets around a math span stay outside it**: `($\mathrm{DNA = 2n}$)`. Brackets that are part of the expression stay inside: `$(V_B)_A$`. Both forms were tested in the editor and render correctly.
- **Prices**: an escaped dollar before a number, `\$5`, becomes `$\$5$`. A dollar sign that is not paired (`سعر $5`), or the price shape `5$ ... 6$` that would be read as one fake equation, cannot be fixed safely: the line is left untouched and `check` reports `unbalanced-dollar`, so fix it by hand (write `\$5` for a price).
- **Display math (`$$`) goes on its own lines, with no direction characters.** A multi-line derivation uses `\begin{aligned} ... \end{aligned}` inside `$$`, one step per line, aligned on `&=`. Do not use `\hline` inside it. A `$$...$$` in the middle of a sentence is turned into inline math, and two touching spans `$a$$b$` get a space between them.
- **No tables.** Use lists. `fix` converts every table into a list on its own: the first cell is the item, the other cells become sub-items prefixed with their column header (`--keep-tables` skips this). A table inside a quote or callout is converted the same way, with the quote marks kept.
- **No decorative horizontal rules** (`---` in the body). `fix` removes them (`--keep-rules` skips this). Front matter and a `---` that underlines a heading line are never touched.
- **After a key's bullets, a following plain list needs a short lead-in sentence** so the two lists do not merge into one. `check` reports `list-after-key-needs-lead-in`.
- **`fix` never guesses**: a line is rewritten only when the result is stable (a second pass changes nothing) and passes the structural checks. A line that cannot be fixed safely stays exactly as it was and `check` reports it, so always read the `check` output after `fix`.
- A Markdown hard line break (two trailing spaces) is kept; other trailing spaces are removed.

## The key (المفتاح) after every LaTeX

There is no symbol list at the top of the file. Instead, every LaTeX that appears gets its own small key, containing only the symbols of that LaTeX, placed right after it. The reader never has to scroll up.

- After a `$$` block: a blank line, then the plain line `المفتاح:`, then one bullet per symbol in the form `- $\mathrm{B}$: كثافة الفيض المغناطيسي`. The text after the colon is a short Arabic definition only, a few words (a definition longer than 14 words gets a warning). Do not use the `حيث` sentence form; this is a deliberate house rule. The key label is plain text, not bold.
- A natural pair may share one bullet, with every letter written as math: `- $\mathrm{r_{A}}$ , $\mathrm{r_{B}}$: بعد السلك عن النقطة $\mathrm{A}$ / عن النقطة $\mathrm{B}$`.
- For inline math inside a sentence, name the thing in Arabic right before the symbol (`نسبة الملح $\mathrm{S}$`). Give a separate key only when the symbol is new or unclear.
- Repeat the same definition every time the symbol appears in a new equation. Repetition is wanted.
- Define everything a student could ask about: letters, subscripts (`in`, `out`, `m`), Greek letters, and constants you introduce yourself. Units written after a number (`\ \mathrm{m}`), plain functions such as `\sin`, `\text{...}` words, and the differential (`d`, and `dt` when `t` is in the key) need no key.

Example:

```
$$
\mathrm{V_{f} = V_{0} \cdot \frac{S_{in}}{S_{out}}}
$$

المفتاح:

- $\mathrm{V_f}$ , $\mathrm{V_0}$: الحجم النهائي / الابتدائي للخلية
- $\mathrm{S_{in}}$ , $\mathrm{S_{out}}$: نسبة الملح داخل الخلية / خارجها
```

## Worked solutions and exam answers

When the file is a set of solved problems, organize it so the student never has to guess. `scaffold` prints this structure; `check` warns when a question misses a section, has them out of order, has no numbered steps, or when the file has no final summary.

- One `##` heading per question, for example `## السؤال $1$: ...`.
- Inside it, `###` sections in this order: فكرة السؤال بكلمات بسيطة; المعطيات (say where each value came from, the figure or the text); المطلوب; الحل بالتفصيل; لماذا باقي الاختيارات خاطئة (for multiple choice); التحقق من الحل; الإجابة النهائية.
- The solution is a sequence of numbered `####` steps (`الخطوة $1$: ...`), each small and with one purpose.
- Write every step in full, as if the student cannot fill any gap: unit conversions, the exact substitution, intermediate arithmetic line by line, and why a formula applies (for example why `\sin` and not `\cos`). Do not abbreviate.
- Where it helps, add a numeric example with chosen values to show the shape of a result, and a second method as a cross-check.
- For multiple choice, explain why each wrong option is wrong and name the trap (radius taken as diameter, wrong unit exponent, resistivity mistaken for conductivity).
- End the file with a numbered summary of final answers (`## ملخص الإجابات النهائية`).
- When the source is an image, enlarge the unclear parts before reading them, and say so plainly if a figure is only approximate.
- Layout: no justified text, no decorative rules, one font family, a compact opening.

## What the script does and does not do

`fix` rewrites: direction characters and isolates, bare Latin and digits, Arabic-Indic digits, edge operators, upright Latin in inline and display math, bold and italic markup (`**`, `***`, `*x*`, `_x_`, `<b>`, `<i>`, `<strong>`, `<em>`: removed, the text stays), `$$` inside a sentence, escaped prices, underscore names, tables including quoted ones (to lists), horizontal rules (removed).

`check` flags but does not fix: leftover bold markup (for example `** text **` with spaces inside, which is not bold in any renderer), an unpaired `$`, an unclosed `$$`, `\hline` or unbalanced braces in display math, a display equation with no key line after it, an empty key, a key bullet that is not `symbols: Arabic definition`, a plain list right after a key, the old `حيث` style, and a top symbol-list heading (a heading containing تعريف or مفاتيح). It warns about equation symbols and Greek letters missing from their key, long key definitions, and worked-solution structure. Write the keys yourself.

Known limits, stated so nobody is surprised:
- Emphasis is detected by pairs: a lone `*` or `_` is left alone, and a pair of literal ones is read as italics unless escaped with a backslash.
- Code is recognized when it is fenced, or indented by four spaces after a blank line outside a list. Anything else that looks like code is treated as text.
- Only the checks above exist for display math; the script never rewrites a `$$` block whose braces do not balance.
- The script cannot see the editor. When a new kind of line misbehaves in Obsidian, ask the user to test the rendered result before changing a rule.

## Check codes

Every ✘ that `check` prints is one of these codes. Each is fixed by `fix` unless the text says it needs you.

- `line-wrap`: an Arabic or math line is missing its RLM + RLI + PDI wrapper.
- `math-isolate`: an inline math span is missing its LRI and PDI.
- `bare-latin-or-digit`: Latin letters or digits sit outside LaTeX in Arabic text.
- `latin-not-upright`: Latin letters inside inline math are not in `\mathrm`.
- `edge-operator`: an operator sits at the edge of a math span next to Arabic.
- `hindi-digits`: Arabic-Indic digits are present.
- `bold-markup-not-wanted`: bold or italic markup is present. A stray `** text **` needs you.
- `table`: a table is present (a table in a quote counts too).
- `horizontal-rule`: a decorative rule is present.
- `unbalanced-dollar`: a `$` cannot be paired, or has the price shape. Needs you.
- `unclosed-display`: a `$$` block has no closing `$$`. Needs you.
- `display-latin-not-upright`: Latin letters inside `$$` are not in `\mathrm`.
- `display-braces-unbalanced`: the braces in a `$$` block do not balance. Needs you.
- `direction-chars-in-display`: a `$$` block contains direction characters.
- `hline-in-display`: a `$$` block contains `\hline`. Needs you.
- `no-key-after-display`: a `$$` block has no `المفتاح:` after it. Needs you.
- `empty-key`: the `المفتاح:` line has no bullets. Needs you.
- `key-bullet-format`: a key bullet is not `symbols: Arabic definition`. Needs you.
- `old-hayth-style-use-key`: a `حيث` sentence follows the equation instead of a key. Needs you.
- `list-after-key-needs-lead-in`: a plain list follows a key with no sentence between. Needs you.
- `top-symbol-list-not-wanted`: a symbol list heading sits at the top of the file. Needs you.

## Files

- `scripts/rtlmd.py`: the tool (`--version` prints the version, currently 2.2.0).
- `scripts/test_rtlmd.py`: self-test, 34 tests plus random idempotency runs. It also checks that every code above is documented here.
- `assets/example_before.md` and `assets/example_after.md`: a before and after pair. The control characters are invisible there, which is the point. The before file contains deliberate mistakes (Arabic-Indic digits, bare Latin, edge operators, bold markers) for the script to fix.
- `assets/example_obsidian_before.md` and `assets/example_obsidian_after.md`: the same idea for Obsidian features (numbered lists, task boxes, callouts, wikilinks, tables including a quoted one, a rule, prices, italics, an underscore name, indented code).
- `AGENTS.md`: the same workflow in the short form that coding agents look for by convention.
- `CHANGELOG.md`: what changed in each version.
