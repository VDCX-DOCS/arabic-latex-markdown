# Instructions for AI agents

This repository holds `rtlmd.py`, a tool that makes Arabic Markdown with LaTeX render correctly in right-to-left editors.

When asked to write, edit, convert or repair a Markdown file whose prose is Arabic and that contains math, Latin words or digits:

1. Read `SKILL.md` first. It is the specification; follow it exactly.
2. Write ordinary Markdown. Do not type the invisible direction characters by hand and do not write bold or italic markup.
3. Run `python scripts/rtlmd.py fix PATH`, then `python scripts/rtlmd.py check PATH`.
4. Repair every failure reported by `check` by hand and run `check` again. Read the warnings too.
5. After changing anything in `scripts/`, run `python scripts/test_rtlmd.py`. It must pass.

Do not hand-edit `assets/*_after.md`; regenerate them from the matching `*_before.md` file with `fix`.
