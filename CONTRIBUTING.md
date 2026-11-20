# Contributing

Bug reports and pull requests are welcome.

## Reporting a problem

Open an issue and include the smallest input line that goes wrong, what you expected, what you got, and the editor you view it in. The tool cannot see your editor, so the rendered result is the most useful evidence. Direction characters are invisible; paste the line inside a code block, or attach the file.

## Changing code or rules

1. Fork the repository and create a branch.
2. Make the change. Rules are documented in `SKILL.md`; if you change behaviour, change the text and add a line to `CHANGELOG.md`.
3. Add a test in `scripts/test_rtlmd.py` for every new behaviour or fixed bug.
4. Run `python scripts/test_rtlmd.py`. It must pass.
5. If an example changed, regenerate the `*_after.md` file with `python scripts/rtlmd.py fix` instead of editing it by hand.
6. Open a pull request that says what changed and why.

Keep the tool dependency-free and compatible with Python 3.9.
