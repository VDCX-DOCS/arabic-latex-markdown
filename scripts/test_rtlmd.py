#!/usr/bin/env python3
"""Self-test for rtlmd 2.2.0. Run:  python scripts/test_rtlmd.py
Prints one status line. Any failure prints the details and exits with 1."""
import contextlib
import io
import os
import pathlib
import random
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import rtlmd as R  # noqa: E402

v = R.visible

# (input line, expected output with control characters shown as <RLM> <RLI> <LRI> <PDI>)
LINE_CASES = [
    ('DNA يتضاعف في الطور البيني، وعدد الكروموسومات ٤٦ ثم يصبح 23 + 23 = 46 عند الإخصاب.', '<RLM><RLI><LRI>$\\mathrm{DNA}$<PDI> يتضاعف في الطور البيني، وعدد الكروموسومات <LRI>$46$<PDI> ثم يصبح <LRI>$23 + 23 = 46$<PDI> عند الإخصاب.<PDI>'),
    ('الملح $S$ = الماء', '<RLM><RLI>الملح <LRI>$\\mathrm{S}$<PDI> = الماء<PDI>'),
    ('الملح $\\mathrm{S =}$ الماء', '<RLM><RLI>الملح <LRI>$\\mathrm{S}$<PDI> = الماء<PDI>'),
    ('ثم $S =$ الماء و$+ x$', '<RLM><RLI>ثم <LRI>$\\mathrm{S}$<PDI> = الماء و+ <LRI>$\\mathrm{x}$<PDI><PDI>'),
    ('النسبة $S_{out} > S_{in}$ هنا', '<RLM><RLI>النسبة <LRI>$\\mathrm{S_{out} > S_{in}}$<PDI> هنا<PDI>'),
    ('($\\mathrm{DNA = 2n}$) و$(V_B)_A$', '<RLM><RLI>(<LRI>$\\mathrm{DNA = 2n}$<PDI>) و<LRI>$\\mathrm{(V_B)_A}$<PDI><PDI>'),
    ('الناتج = 4', '<RLM><RLI>الناتج = <LRI>$4$<PDI><PDI>'),
    ('## 1. اختبار', '## <RLM><RLI><LRI>$1$<PDI>. اختبار<PDI>'),
    ('# عنوان DNA', '# <RLM><RLI>عنوان <LRI>$\\mathrm{DNA}$<PDI><PDI>'),
    ('نقطة A وقيمة 3.5 م/ث', '<RLM><RLI>نقطة <LRI>$\\mathrm{A}$<PDI> وقيمة <LRI>$3.5$<PDI> م/ث<PDI>'),
    ('سعر 50% و100 g', '<RLM><RLI>سعر <LRI>$50$<PDI>% و<LRI>$100$<PDI> <LRI>$\\mathrm{g}$<PDI><PDI>'),
    ('العدد ٤٦ و۱۲', '<RLM><RLI>العدد <LRI>$46$<PDI> و<LRI>$12$<PDI><PDI>'),
    # list markers, task boxes, callouts, quotes stay outside the direction wrapper
    ('1. الخطوة الأولى', '1. <RLM><RLI>الخطوة الأولى<PDI>'),
    ('2) الخطوة 2 تعطي $a=b$', '2) <RLM><RLI>الخطوة <LRI>$2$<PDI> تعطي <LRI>$\\mathrm{a=b}$<PDI><PDI>'),
    ('- [ ] مهمة 4', '- [ ] <RLM><RLI>مهمة <LRI>$4$<PDI><PDI>'),
    ('- [x] تمت 5', '- [x] <RLM><RLI>تمت <LRI>$5$<PDI><PDI>'),
    ('> [!note] ملاحظة 6', '> [!note] <RLM><RLI>ملاحظة <LRI>$6$<PDI><PDI>'),
    ('> [!faq]- سؤال 7', '> [!faq]- <RLM><RLI>سؤال <LRI>$7$<PDI><PDI>'),
    ('> > نص 5', '> > <RLM><RLI>نص <LRI>$5$<PDI><PDI>'),
    ('    - نص متداخل 5', '    - <RLM><RLI>نص متداخل <LRI>$5$<PDI><PDI>'),
    # Obsidian syntax is never touched
    ('انظر [[ملاحظة 3]] و #tag1 ونص ^blk-1', '<RLM><RLI>انظر [[ملاحظة 3]] و #tag1 ونص ^blk-1<PDI>'),
    ('![[صورة 1.png]]', '![[صورة 1.png]]'),
    ('![صورة 2](img 1.png)', '![صورة 2](img 1.png)'),
    ('نص[^1] هنا', '<RLM><RLI>نص[^1] هنا<PDI>'),
    ('[^1]: حاشية 5', '[^1]: <RLM><RLI>حاشية <LRI>$5$<PDI><PDI>'),
    ('انظر [الرابط 5](http://a.b/c) هنا', '<RLM><RLI>انظر [الرابط <LRI>$5$<PDI>](http://a.b/c) هنا<PDI>'),
    # dollars
    ('الناتج = 4 والسعر \\$5 فقط', '<RLM><RLI>الناتج = <LRI>$4$<PDI> والسعر <LRI>$\\$5$<PDI> فقط<PDI>'),
    ('15 \\$ و\\$ 7', '<RLM><RLI><LRI>$15$<PDI> \\$ و\\$ <LRI>$7$<PDI><PDI>'),
    ('وصيغة $$x^2$$ داخل السطر', '<RLM><RLI>وصيغة <LRI>$\\mathrm{x^2}$<PDI> داخل السطر<PDI>'),
    ('$$x^2$$ بداية السطر نص', '<RLM><RLI><LRI>$\\mathrm{x^2}$<PDI> بداية السطر نص<PDI>'),
    ('نص $a$$b$ ملتصق', '<RLM><RLI>نص <LRI>$\\mathrm{a}$<PDI> <LRI>$\\mathrm{b}$<PDI> ملتصق<PDI>'),
    # Latin upright also in math that has commands
    ('الصيغة $\\frac{a}{b}$ و$\\vec{F}$ و$\\sin x$', '<RLM><RLI>الصيغة <LRI>$\\frac{\\mathrm{a}}{\\mathrm{b}}$<PDI> و<LRI>$\\vec{\\mathrm{F}}$<PDI> و<LRI>$\\sin \\mathrm{x}$<PDI><PDI>'),
    ('القيمة $\\Phi_m$ و$x_{ab}$', '<RLM><RLI>القيمة <LRI>$\\Phi_{\\mathrm{m}}$<PDI> و<LRI>$\\mathrm{x_{ab}}$<PDI><PDI>'),
    ('نص <!-- تعليق 5 --> ونص &amp; 3', '<RLM><RLI>نص <!-- تعليق 5 --> ونص &amp; <LRI>$3$<PDI><PDI>'),
    ('الرابط https://example.com/a?x=1 و`ملف 5.py`', '<RLM><RLI>الرابط https://example.com/a?x=1 و`ملف 5.py`<PDI>'),
    # no bold or italic markup at all: the markers go, the text stays
    ('نسبة **المفتاح:** و**(مهم)**', '<RLM><RLI>نسبة المفتاح: و(مهم)<PDI>'),
    ('الملح**$S$**الماء', '<RLM><RLI>الملح<LRI>$\\mathrm{S}$<PDI>الماء<PDI>'),
    ('***مهم جدًا*** هنا', '<RLM><RLI>مهم جدًا هنا<PDI>'),
    ('نص <b>جاهز 5</b> و<i>مائل</i>', '<RLM><RLI>نص جاهز <LRI>$5$<PDI> ومائل<PDI>'),
    # whitespace and lines with nothing to wrap
    ('سطر بنهاية مزدوجة  ', '<RLM><RLI>سطر بنهاية مزدوجة<PDI>  '),
    ('English only line 5', 'English only line 5'),
    ('- ', '-'),
    ('- [ ] ', '- [ ]'),
    ('$x$', '<RLM><RLI><LRI>$\\mathrm{x}$<PDI><PDI>'),
    ('- **Note:** plain english', '- Note: plain english'),
    ('نص `**code**` و[**رابط**](http://a.b/**)', '<RLM><RLI>نص `**code**` و[رابط](http://a.b/**)<PDI>'),
    # italics go too; file names with underscores and products with asterisks stay one piece
    ('نص *مائل 5* و _آخر_ هنا', '<RLM><RLI>نص مائل <LRI>$5$<PDI> و آخر هنا<PDI>'),
    ('الملف my_file_name هنا', '<RLM><RLI>الملف <LRI>$\\mathrm{my\\_file\\_name}$<PDI> هنا<PDI>'),
    ('القيمة 5*3*2 هنا', '<RLM><RLI>القيمة <LRI>$5$<PDI>*<LRI>$3$<PDI>*<LRI>$2$<PDI> هنا<PDI>'),
    ('نص `*x*` و[[_ن_]] و$a*b*c$', '<RLM><RLI>نص `*x*` و[[_ن_]] و<LRI>$\\mathrm{a*b*c}$<PDI><PDI>'),
    # a plain indented line keeps its indentation (it continues a list item)
    ('    استمرار 5 للعنصر', '    <RLM><RLI>استمرار <LRI>$5$<PDI> للعنصر<PDI>'),
    # numbers: thousands separators, decimals and exponents stay in one span
    ('ثم 1,000 و 12,5 و 3.5', '<RLM><RLI>ثم <LRI>$1,000$<PDI> و <LRI>$12,5$<PDI> و <LRI>$3.5$<PDI><PDI>'),
    ('القيمة 1.5e3 هنا', '<RLM><RLI>القيمة <LRI>$\\mathrm{1.5e3}$<PDI> هنا<PDI>'),
    ('نقطة 5, ثم 6', '<RLM><RLI>نقطة <LRI>$5$<PDI>, ثم <LRI>$6$<PDI><PDI>'),
    ('الفرق $ x - y $ بينهما', '<RLM><RLI>الفرق <LRI>$\\mathrm{x - y}$<PDI> بينهما<PDI>'),
]
# These inputs are deliberately left for a human (check must still flag them).
STILL_FLAGGED = {"سعر $5 غير متوازن", "نص ** ليس عريضًا ** هنا", "السعر 5$ والثاني 6$ فقط", "طاقة $E = 5$ ثم 6$ فقط"}


def run_cli(*args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = R.main(list(args))
    return code, buf.getvalue()


class TestLines(unittest.TestCase):
    def test_golden(self):
        for src, exp in LINE_CASES:
            with self.subTest(src=src):
                self.assertEqual(v(R.fix_line(src)), exp)

    def test_idempotent_and_clean(self):
        for src, _ in LINE_CASES:
            with self.subTest(src=src):
                once = R.fix_line(src)
                self.assertEqual(R.fix_line(once), once)
                self.assertEqual(R.check_line(once), [], v(once))

    def test_left_for_human(self):
        for src in STILL_FLAGGED:
            with self.subTest(src=src):
                self.assertTrue(R.check_line(R.fix_line(src)))

    def test_no_bold_markup_survives(self):
        text = "# عنوان\n\n**المفتاح:** نص <b>و5</b>\n- **الخطوة 1:** <i>احسب</i> و<strong>x</strong>\n> **تنبيه (2)**\nEnglish **bold** line\n"
        new, _ = R.fix_text(text)
        self.assertNotIn("**", new)
        self.assertNotRegex(new, r"</?(?:b|i|strong|em)>")
        self.assertEqual(R.check_text(new)[0], [])
        self.assertEqual(R.fix_text(new)[0], new)
        left, _ = R.check_text("نص ** ليس عريضًا ** هنا")
        self.assertIn("bold-markup-not-wanted", {c for _, c in left})
        left, _ = R.check_text("نص <b>x</b> هنا")
        self.assertIn("bold-markup-not-wanted", {c for _, c in left})

    def test_safety_net_keeps_unfixable_lines(self):
        for src in ["- 5$ $$y$$ 3.5 \u0664\u0666 ~~س 3~~ 5$ #t1", "- [ ] 5$ $$y$$ 5 نص ) 5$"]:
            with self.subTest(src=src):
                self.assertEqual(R.fix_line(src), src)
                self.assertTrue(R.check_line(R.fix_line(src)))

    def test_fuzz_idempotent(self):
        rnd = random.Random(7)
        pieces = ["نص", "كلمة", "DNA", "x", "5", "٤٦", "$x$", "$a=b$", "**غامق**", "`code 1`", "[[ملاحظة 3]]",
                  "#tag1", "\\$5", "$$y^2$$", "<b>t</b>", "(", ")", "=", "+", "-", "A", "3.5", "m/s", "1,000", "1.5e3", "5$", "*مائل*", "_ب_", "my_file_name", "5*3", "a * b",
                  "$\\frac{a}{b}$", "https://e.com/a", "&amp;", "$\\Phi_m$", "[رابط 2](http://a.b)", "%"]
        prefixes = ["", "- ", "1. ", "> ", "## ", "- [ ] ", "> [!note] ", "  - "]
        for _ in range(4000):
            line = rnd.choice(prefixes) + " ".join(rnd.choice(pieces) for _ in range(rnd.randint(1, 8)))
            once = R.fix_line(line)
            self.assertEqual(R.fix_line(once), once, repr(line))
            if once != line.rstrip():       # a rewritten line must be clean; a kept one is reported by check
                self.assertFalse(R.SAFETY_CODES & set(R.check_line(once)), "%r -> %s" % (line, v(once)))


def CTRL_FREE(s):
    return R.CTRL.sub("", s)


class TestMath(unittest.TestCase):
    def test_upright(self):
        cases = {
            r"\Phi_m": r"\Phi_{\mathrm{m}}",
            r"x_ab": r"\mathrm{x}_{\mathrm{a}}\mathrm{b}",
            r"\Phi_\mathrm{m}": r"\Phi_{\mathrm{m}}",
            r"\text{if } x": r"\text{if } \mathrm{x}",
            r"\begin{array}{cc} a & b \end{array}": r"\begin{array}{cc} \mathrm{a} & \mathrm{b} \end{array}",
            r"\left\{ a \right\}": r"\left\{ \mathrm{a} \right\}",
            r"\mathbf{F} = m\vec{a}": r"\mathbf{F} = \mathrm{m}\vec{\mathrm{a}}",
            r"\sqrt[3]{x}": r"\sqrt[3]{\mathrm{x}}",
            "x % c\ny": "\\mathrm{x} % c\n\\mathrm{y}",     # a % comment runs to the end of its line
        }
        for src, exp in cases.items():
            with self.subTest(src=src):
                self.assertEqual(R.upright_latin(src), exp)
                self.assertEqual(R.upright_latin(exp), exp)

    def test_unbalanced_braces_raise(self):
        with self.assertRaises(ValueError):
            R.upright_latin(r"\text{abc")


class TestBlocks(unittest.TestCase):
    def test_display_fixed_and_idempotent(self):
        src = "$$\n\\begin{aligned}\nF &= m a \\\\\nW &= F d \\cos\\theta\n\\end{aligned}\n$$"
        new, _ = R.fix_text(src)
        self.assertIn("\\mathrm{F} &= \\mathrm{m} \\mathrm{a}", new)
        self.assertIn("\\begin{aligned}", new)
        self.assertEqual(R.fix_text(new)[0], new)

    def test_display_hindi_and_direction_chars(self):
        new, _ = R.fix_text("$$\nx = \u0664\u0662\u200f\n$$")
        self.assertNotIn("\u200f", new)
        self.assertIn("42", new)

    def test_display_problems_flagged(self):
        iss, _ = R.check_text("$$\n\\hline a\n$$\n\nالمفتاح:\n\n- $\\mathrm{a}$: رمز")
        codes = {c for _, c in iss}
        self.assertIn("hline-in-display", codes)
        self.assertIn("display-latin-not-upright", codes)
        iss, _ = R.check_text("$$\nx")
        self.assertIn("unclosed-display", {c for _, c in iss})

    def test_table_to_list(self):
        src = "| الرمز | المعنى |\n|---|---|\n| $V$ | الجهد |\n| a\\|b | `x|y` |\n\nنص بعد"
        new, st = R.fix_text(src)
        self.assertEqual(st["tables"], 1)
        self.assertNotIn("|---", new)
        self.assertIn("a|b", new)
        self.assertIn("`x|y`", new)
        self.assertEqual(R.fix_text(new)[0], new)
        kept, _ = R.fix_text(src, keep_tables=True)
        self.assertIn("|---|---|", kept)
        self.assertIn("table", {c for _, c in R.check_text(kept)[0]})

    def test_header_only_table_keeps_text(self):
        new, _ = R.fix_text("| أ | ب |\n|---|---|")
        self.assertIn("أ", new)
        self.assertIn("ب", new)

    def test_rules_removed_but_front_matter_and_setext_kept(self):
        src = "---\ntags: [a]\n---\n# عنوان\n\n---\n\nنص\nعنوان ثانوي\n---\n"
        new, st = R.fix_text(src)
        self.assertEqual(st["rules"], 1)
        self.assertTrue(new.startswith("---\ntags: [a]\n---\n"))
        self.assertTrue(new.endswith("\u2069\n---\n"), repr(new))      # the setext underline stays
        self.assertEqual(R.fix_text(new)[0], new)
        kept, st2 = R.fix_text(src, keep_rules=True)
        self.assertEqual(st2["rules"], 0)
        self.assertIn("horizontal-rule", {c for _, c in R.check_text(kept)[0]})

    def test_code_fences_untouched(self):
        src = "```py\nx = ١٢ DNA\n```\n~~~\ny 5\n~~~\n````\n```\nz 5\n````"
        self.assertEqual(R.fix_text(src)[0], src)

    def test_quote_table_and_indented_code(self):
        new, st = R.fix_text("> | أ | ب |\n> |---|---|\n> | 1 | 2 |\n\n    code 5 DNA\n\nنص")
        self.assertEqual(st["tables"], 1)
        self.assertNotIn("|---", new)
        self.assertTrue(new.split("\n")[0].startswith("> - "))
        self.assertIn("\n    code 5 DNA\n", new)
        self.assertEqual(R.fix_text(new)[0], new)
        self.assertEqual(R.check_text(new)[0], [])

    def test_list_continuation_is_not_code_and_keeps_indent(self):
        new, _ = R.fix_text("1. عنصر\n\n    استمرار 5 للعنصر\n\nنص")
        self.assertIn("\n    \u200f\u2067استمرار", new)
        self.assertEqual(R.fix_text(new)[0], new)
        # directly after a paragraph, four spaces are a continuation, not code
        new, _ = R.fix_text("نص\n    استمرار 5\n")
        self.assertIn("\u200f\u2067استمرار", new)

    def test_display_in_callout(self):
        src = "> $$\n> a = b\n> $$"
        new, _ = R.fix_text(src)
        self.assertIn("> \\mathrm{a} = \\mathrm{b}", new)


class TestKey(unittest.TestCase):
    def _issues(self, text):
        i, w = R.check_text(R.fix_text(text)[0])
        return {c for _, c in i}, [m for _, m in w]

    def test_good_key(self):
        text = "$$\n\\mathrm{V = I R}\n$$\n\nالمفتاح:\n\n- $\\mathrm{V}$: الجهد\n- $\\mathrm{I}$ , $\\mathrm{R}$: التيار / المقاومة"
        codes, warns = self._issues(text)
        self.assertEqual((codes, warns), (set(), []))

    def test_problems(self):
        base = "$$\n\\mathrm{V = I R}\n$$\n\n"
        self.assertIn("no-key-after-display", self._issues(base + "نص")[0])
        self.assertIn("old-hayth-style-use-key", self._issues(base + "حيث V جهد")[0])
        self.assertIn("empty-key", self._issues(base + "المفتاح:\n\nنص")[0])
        self.assertIn("key-bullet-format", self._issues(base + "المفتاح:\n\n- $\\mathrm{V}$ الجهد")[0])
        self.assertIn("key-bullet-format", self._issues(base + "المفتاح:\n\n- $\\mathrm{V}$: voltage")[0])
        self.assertIn("list-after-key-needs-lead-in",
                      self._issues(base + "المفتاح:\n\n- $\\mathrm{V}$: الجهد\n\n- عنصر عادي")[0])
        self.assertIn("top-symbol-list-not-wanted", self._issues("## تعريف الرموز\n")[0])

    def test_missing_symbols_and_greek(self):
        base = "$$\n\\mathrm{V} = \\alpha \\mathrm{I}\n$$\n\nالمفتاح:\n\n- $\\mathrm{V}$: الجهد"
        _, warns = self._issues(base)
        self.assertTrue(any("I" in w for w in warns))
        self.assertTrue(any("alpha" in w for w in warns))

    def test_differential_needs_no_key(self):
        text = "$$\n\\frac{\\mathrm{d}\\Phi}{\\mathrm{dt}}\n$$\n\nالمفتاح:\n\n- $\\Phi$: التدفق\n- $\\mathrm{t}$: الزمن"
        self.assertEqual(self._issues(text), (set(), []))

    def test_long_definition_warns(self):
        text = "$$\n\\mathrm{V}\n$$\n\nالمفتاح:\n\n- $\\mathrm{V}$: " + " ".join(["كلمة"] * 15)
        self.assertTrue(any("long" in w for w in self._issues(text)[1]))


class TestDocs(unittest.TestCase):
    def test_every_issue_code_is_documented(self):
        import re
        src = pathlib.Path(R.__file__).read_text(encoding="utf-8")
        doc_path = pathlib.Path(R.__file__).resolve().parent.parent / "SKILL.md"
        if not doc_path.exists():
            self.skipTest("SKILL.md not next to the scripts folder")
        doc = doc_path.read_text(encoding="utf-8")
        codes = set()
        for line in src.split("\n"):
            if re.search(r"\b(?:iss|issues)\.append\(", line) or re.search(r"\(\w+ \+ 1, \"", line):
                codes.update(re.findall(r'"([a-z]+(?:-[a-z]+)*)"', line))
        codes.discard("")
        self.assertGreater(len(codes), 15)
        missing = sorted(c for c in codes if "`%s`" % c not in doc)
        self.assertEqual(missing, [], "issue codes missing from SKILL.md")

    def test_version_is_documented(self):
        doc_path = pathlib.Path(R.__file__).resolve().parent.parent / "SKILL.md"
        if doc_path.exists():
            self.assertIn("v" + R.__version__, doc_path.read_text(encoding="utf-8"))


class TestSolutions(unittest.TestCase):
    def test_scaffold_is_clean(self):
        new, _ = R.fix_text(R.scaffold(2))
        self.assertEqual(R.check_text(new), ([], []))
        self.assertEqual(R.fix_text(new)[0], new)

    def test_missing_and_order(self):
        text = "## السؤال 1: س\n\n### المعطيات\n\n### المطلوب\n\n### فكرة السؤال بكلمات بسيطة\n"
        _, warns = R.check_text(text)
        msgs = " | ".join(m for _, m in warns)
        self.assertIn("missing section «الحل بالتفصيل»", msgs)
        self.assertIn("out of the expected order", msgs)
        self.assertIn("no final summary", msgs)

    def test_not_a_solution_file(self):
        self.assertEqual(R.check_text("## درس\n\nنص")[1], [])


class TestFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_crlf_and_bom_preserved_and_no_rewrite_when_clean(self):
        p = self.dir / "a.md"
        p.write_bytes(b"\xef\xbb\xbf" + "نص 5\r\nسطر ثان\r\n".encode("utf-8"))
        self.assertEqual(run_cli("fix", str(p))[0], 0)
        raw = p.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(raw.count(b"\r\n"), raw.count(b"\n"))
        m = p.stat().st_mtime_ns
        self.assertEqual(run_cli("fix", str(p))[0], 0)
        self.assertEqual(p.stat().st_mtime_ns, m)

    def test_diff_writes_nothing(self):
        p = self.dir / "a.md"
        p.write_text("نص 5\n", encoding="utf-8")
        code, out = run_cli("fix", str(p), "--diff")
        self.assertEqual(p.read_text(encoding="utf-8"), "نص 5\n")
        self.assertIn("<RLM>", out)

    def test_folder_is_content_based(self):
        (self.dir / "a.txt").write_text("نص 5\n", encoding="utf-8")
        (self.dir / "b.md").write_text("english only 5\n", encoding="utf-8")
        (self.dir / ".hidden").mkdir()
        (self.dir / ".hidden" / "c.md").write_text("نص 5\n", encoding="utf-8")
        (self.dir / "bin.dat").write_bytes(b"\x00\x01" + "نص".encode("utf-8"))
        run_cli("fix", str(self.dir))
        self.assertIn("\u200f", (self.dir / "a.txt").read_text(encoding="utf-8"))
        self.assertEqual((self.dir / "b.md").read_text(encoding="utf-8"), "english only 5\n")
        self.assertEqual((self.dir / ".hidden" / "c.md").read_text(encoding="utf-8"), "نص 5\n")

    def test_output_file_and_multiple_inputs(self):
        a, b, o = self.dir / "a.md", self.dir / "b.md", self.dir / "o.md"
        a.write_text("نص 5\n", encoding="utf-8")
        b.write_text("نص 6\n", encoding="utf-8")
        self.assertEqual(run_cli("fix", str(a), "-o", str(o))[0], 0)
        self.assertEqual(a.read_text(encoding="utf-8"), "نص 5\n")
        self.assertIn("\u200f", o.read_text(encoding="utf-8"))
        self.assertEqual(run_cli("fix", str(a), str(b), "-o", str(o))[0], 2)

    def test_exit_codes(self):
        p = self.dir / "a.md"
        p.write_text("نص 5\n", encoding="utf-8")
        self.assertEqual(run_cli("check", str(p))[0], 1)
        run_cli("fix", str(p))
        self.assertEqual(run_cli("check", str(p))[0], 0)
        self.assertEqual(run_cli("check", str(self.dir / "missing.md"))[0], 2)

    def test_full_note(self):
        p = self.dir / "n.md"
        p.write_text(
            "---\ntags: [x]\n---\n# درس 3\n\n> [!note] ملاحظة 6\n> نص DNA\n\n1. الخطوة تعطي $V = I R$\n"
            "- [ ] مهمة 4\n\n| الرمز | المعنى |\n|---|---|\n| $V$ | الجهد |\n\n---\n\nنص **مهم:** وسعر \\$5\n\n"
            "$$\n\\Phi_m = B A\n$$\n\nالمفتاح:\n\n- $\\Phi_\\mathrm{m}$: التدفق\n- $\\mathrm{B}$: الفيض\n- $\\mathrm{A}$: المساحة\n",
            encoding="utf-8")
        code, _ = run_cli("fix", str(p))
        self.assertEqual(code, 0)
        text = p.read_text(encoding="utf-8")
        self.assertEqual(R.fix_text(text)[0], text)
        self.assertEqual(R.check_text(text), ([], []))
        self.assertIn("1. \u200f\u2067", text)
        self.assertNotIn("|---", text)


def main():
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    buf = io.StringIO()
    res = unittest.TextTestRunner(stream=buf, verbosity=0).run(suite)
    if res.wasSuccessful():
        print("\u2714 rtlmd %s: %d tests passed" % (R.__version__, res.testsRun))
        return 0
    print(buf.getvalue())
    print("\u2718 rtlmd %s: %d failures, %d errors" % (R.__version__, len(res.failures), len(res.errors)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
