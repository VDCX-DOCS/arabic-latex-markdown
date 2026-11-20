#!/usr/bin/env python3
"""rtlmd 2.2.0: make Arabic Markdown with LaTeX bidi-safe in RTL editors (Obsidian).

  rtlmd.py fix   PATH... [-o OUT] [--diff] [--keep-tables] [--keep-rules]
  rtlmd.py check PATH... [--strict]
  rtlmd.py scaffold [N]
  rtlmd.py --version

PATH is a file or a folder. Inside a folder, files are picked by content (UTF-8 text that
contains Arabic), never by extension; folders whose name starts with "." are skipped.
fix is idempotent and only rewrites a file when something changed.
check exits with 1 on any issue (and on warnings too with --strict).
"""
import argparse
import difflib
import os
import pathlib
import re
import sys
import tempfile

__version__ = "2.2.0"

RLM, RLI, LRI, PDI = "\u200f", "\u2067", "\u2066", "\u2069"
CTRL = re.compile("[\u200e\u200f\u2066-\u2069]")
AR = re.compile("[\u0600-\u06FF]")
HINDI_RE = re.compile("[\u0660-\u0669\u06f0-\u06f9]")
HINDI = {ord(c): str(i) for i, c in enumerate("\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669")}
HINDI.update({ord(c): str(i) for i, c in enumerate("\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9")})
OPS = r"=+\-\u2212<>\u2248\u2192\u2190\u21d2\u2260\u2264\u2265\u00d7\u00f7"
OPC = "[" + OPS + "]"
OPC_NM = "[=+<>\u2248\u2192\u2190\u21d2\u2260\u2264\u2265\u00d7\u00f7]"  # without minus (a sign)

KEY = "المفتاح:"
HAYTH = "حيث"

# ---------------------------------------------------------------- protected spans
# Inline math: one pair of single dollars; an escaped dollar (\$) inside is allowed.
INL = r"(?<![\$\\])\$(?!\$)(?:\\.|[^$\\\n])+\$(?!\$)"
_PROT_PARTS = [
    r"`[^`\n]*`",                                    # code span
    r"<!--.*?-->",                                   # html comment
    r"%%.*?%%",                                      # Obsidian comment
    r"!\[[^\]\n]*\]\([^)\n]*\)",                     # image
    r"!?\[\[[^\]\n]*\]\]",                           # wikilink / embed
    r"\[\^[^\]\n]+\]",                               # footnote reference
    r"</?[A-Za-z][^>\n]*>",                          # html tag
    r"&(?:[A-Za-z][A-Za-z0-9]*|#[0-9]+|#[xX][0-9A-Fa-f]+);",  # html entity
    r"\]\([^)\n]*\)",                                # link target
    r"https?://\S+",                                 # url
    r"(?<![\w/&])#(?=[\w/\-]*[^\W\d])[\w/\-]+",      # tag
    r"(?<=\s)\^[A-Za-z0-9\-]+(?=\s*$)",              # block id
    INL,
]
PROT = re.compile("(" + "|".join(_PROT_PARTS) + ")")
INLINE = re.compile(INL)

# Markers that stay outside the direction wrapper: quote, callout, list, task box,
# ordered number, heading, footnote definition.
_BQ = r"[ \t]*>[ \t]*(?:\[![A-Za-z\-]+\][+\-]?[ \t]*)?"
_LI = r"[ \t]*(?:[-*+]|\d{1,9}[.)])[ \t]+(?:\[[^\]\n]\][ \t]+)?"
_HD = r"[ \t]*#{1,6}[ \t]+"
_FD = r"[ \t]*\[\^[^\]\n]+\]:[ \t]+"
PREFIX = re.compile(r"^((?:%s|%s)*(?:%s|%s)?[ \t]*)" % (_BQ, _LI, _HD, _FD))   # trailing [ \t]*: keep a plain indented line indented

QUOTE = re.compile(r"^(?:[ \t]*>)+[ \t]?")
FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
RULE = re.compile(r"(?:-[ \t]*){3,}|(?:\*[ \t]*){3,}|(?:_[ \t]*){3,}")
DELIM = re.compile(r"^[ \t]*\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$")
BULLET = re.compile(r"^\s*[-*+]\s+")
LISTLINE = re.compile(r"^\s*(?:[-*+]|\d{1,9}[.)])\s+")
NUM = r"(?:[A-Za-z0-9]+(?:_[A-Za-z0-9]+)+|[A-Za-z0-9]+(?:[.,][0-9]+)*[A-Za-z0-9]*)"     # 5, 3.5, 1,000, 1.5e3, DNA, x2
CHAIN = re.compile(r"(?<![A-Za-z0-9\\])" + NUM + r"(?:\s*" + OPC + r"\s*" + NUM + r")*")
ITALIC_STAR = re.compile(r"(?<![\w*\\\x00])\*(?=[^\s*\x00])([^*\n]+?)(?<=[^\s*\x00])\*(?![\w*\x00])")
ITALIC_US = re.compile(r"(?<![\w_\\\x00])_(?=[^\s_\x00])([^_\n]+?)(?<=[^\s_\x00])_(?![\w_\x00])")
BOLD3 = re.compile(r"\*\*\*(?=\S)(.+?)(?<=\S)\*\*\*")
BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*")


# ---------------------------------------------------------------- LaTeX helpers
def balanced(s):
    d = 0
    for c in s:
        if c == "{":
            d += 1
        elif c == "}":
            d -= 1
            if d < 0:
                return False
    return d == 0


def split_edges(inner):
    """Return (lead, core, trail): operators at the edges of a math span."""
    s, lead, trail, wrap = inner.strip(), "", "", False
    m = re.fullmatch(r"\\mathrm\{(.*)\}", s, re.S)
    if m and balanced(m.group(1)):
        s, wrap = m.group(1).strip(), True
    while True:
        m = re.match(r"(%s+)\s*" % OPC_NM, s) or re.match(r"([-\u2212])\s+", s)
        if not m:
            break
        lead += m.group(1) + " "
        s = s[m.end():]
    while True:
        m = re.search(r"\s*(%s+)\s*$" % OPC, s)
        if not m:
            break
        trail = " " + m.group(1) + trail
        s = s[:m.start()]
    core = (r"\mathrm{%s}" % s if wrap and s else s)
    return lead, core, trail


# Commands whose braces hold text, an environment name or a length: copied untouched.
VERB = frozenset((
    "mathrm text textbf textit textrm textsf texttt mathbf mathit mathbb mathcal mathfrak mathsf "
    "mathtt operatorname boldsymbol bm begin end color textcolor hspace vspace label tag ref eqref "
    "href url pagecolor colorbox mbox").split())
ARRAYLIKE = frozenset("array tabular subarray alignedat alignat xalignat tabularx".split())
_CMD = re.compile(r"\\([A-Za-z]+)\*?")


def _group_end(s, i):
    """s[i] == '{'. Return the index after its matching '}'. Raise ValueError if unbalanced."""
    d, j = 0, i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "{":
            d += 1
        elif c == "}":
            d -= 1
            if d == 0:
                return j + 1
        j += 1
    raise ValueError("unbalanced braces")


def _verbatim_arg(s, i):
    """Index after an optional space and one {...} group starting at i, or i if there is none."""
    j = i
    while j < len(s) and s[j] in " \t":
        j += 1
    if j < len(s) and s[j] == "{":
        return _group_end(s, j), j
    return i, j


def upright_latin(s):
    """Put every Latin letter run of a LaTeX string in \\mathrm{...}, except inside commands that
    take text or a name. Idempotent. Raises ValueError when braces do not balance."""
    out, i, n = [], 0, len(s)
    while i < n:
        ch = s[i]
        if ch == "\\":
            m = _CMD.match(s, i)
            if not m:
                out.append(s[i:i + 2])
                i += 2
                continue
            name = m.group(1)
            braced = name == "mathrm" and bool(out) and out[-1][-1:] in ("_", "^")
            out.append("{" + m.group(0) if braced else m.group(0))   # _\mathrm{m} -> _{\mathrm{m}}
            i = m.end()
            if name in VERB:
                k, j = _verbatim_arg(s, i)
                if k != i:
                    out.append(s[i:k])
                    arg = s[j + 1:k - 1]
                    i = k
                    if name == "begin" and arg in ARRAYLIKE:
                        k2, _ = _verbatim_arg(s, i)
                        out.append(s[i:k2])
                        i = k2
            if braced:
                out.append("}")
            continue
        if ch == "%":
            j = s.find("\n", i)
            j = n if j < 0 else j
            out.append(s[i:j])
            i = j
            continue
        if ch.isascii() and ch.isalpha():
            j = i
            while j < n and s[j].isascii() and s[j].isalpha():
                j += 1
            run = s[i:j]
            if out and out[-1][-1:] in ("_", "^"):     # x_a: only the first letter is the subscript
                out.append("{\\mathrm{%s}}" % run[0])
                run = run[1:]
            if run:
                out.append("\\mathrm{%s}" % run)
            i = j
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def norm_math_token(p):
    """Normalize one inline math token ($...$): edge operators out, Latin upright."""
    lead, core, trail = split_edges(p[1:-1])
    if core:
        if "\\" in core:
            try:
                core = upright_latin(core)
            except ValueError:
                pass
        elif re.search("[A-Za-z]", core):
            core = r"\mathrm{%s}" % core
    return lead + ("$%s$" % core if core else "") + trail


# ---------------------------------------------------------------- line level fixes
def wrap_bare(t):
    def f(m):
        ch = m.group(0)
        return "$" + (r"\mathrm{%s}" % ch.replace("_", r"\_") if re.search("[A-Za-z]", ch) else ch) + "$"
    return CHAIN.sub(f, t)


EMPH_TAG = re.compile(r"</?(?:b|i|strong|em)\s*>", re.I)
EMPH_HOLD = re.compile("(" + "|".join([
    r"`[^`\n]*`", INL, r"<!--.*?-->", r"%%.*?%%", r"!\[[^\]\n]*\]\([^)\n]*\)", r"!?\[\[[^\]\n]*\]\]",
    r"\]\([^)\n]*\)", r"https?://\S+"]) + ")")


def strip_emphasis(c):
    """No bold or italic markup at all (it does not render in the verified Obsidian setup, neither
    as ** nor as <b>): **x**, ***x***, *x*, _x_, <b>, <i>, <strong>, <em> are removed and the text
    stays. Code, math, link targets, wikilinks, comments and URLs are left alone."""
    held = []

    def hold(m):
        held.append(m.group(0))
        return "\x00%d\x00" % (len(held) - 1)

    t = EMPH_HOLD.sub(hold, c)
    t = EMPH_TAG.sub("", t)
    t = BOLD3.sub(r"\1", t)
    t = BOLD.sub(r"\1", t)
    t = ITALIC_STAR.sub(r"\1", t)
    t = ITALIC_US.sub(r"\1", t)
    return re.sub("\x00(\\d+)\x00", lambda m: held[int(m.group(1))], t)


def _inline_dd(t):
    """$$x$$ in the middle of a sentence is inline math; $a$$b$ (touching spans) gets a space."""
    t = re.sub(r"\$\$([^$\n]+?)\$\$", r"$\1$", t)
    return re.sub(r"(?<=[^\s$])\$\$(?=[^\s$])", "$ $", t)


def _currency(t):
    """An escaped dollar before a number is a price: \\$5 -> $\\$5$."""
    return re.sub(r"\\\$(\d[\d,]*(?:\.\d+)?)", lambda m: "$\\$%s$" % m.group(1), t)


def dollars_balanced(plain):
    """False when the dollars cannot be paired safely: an odd count, or the price shape
    '5$ ... 6$' (a digit, a lone dollar, a space) that would be read as one fake math span."""
    t = re.sub(r"`[^`\n]*`", "", plain)
    t = re.sub(r"\\.", "", t)
    if t.count("$") % 2:
        return False
    return not re.search(r"\d\$\s", t) or not any(
        m.group(0)[1:2].isspace() and m.start() > 0 and t[m.start() - 1].isdigit() for m in INLINE.finditer(t))


def fix_content(c):
    c = strip_emphasis(CTRL.sub("", c).translate(HINDI))
    out = []
    for i, p in enumerate(PROT.split(c)):
        out.append(p if i % 2 else _inline_dd(_currency(p)))
    s = "".join(out)
    out = []
    for i, p in enumerate(PROT.split(s)):
        if i % 2 == 0:
            out.append(wrap_bare(p))
        elif p.startswith("$"):
            out.append(norm_math_token(p))
        else:
            out.append(p)
    s = "".join(out)
    return "".join(LRI + p + PDI if i % 2 and p.startswith("$") else p for i, p in enumerate(PROT.split(s)))


def split_line(line):
    body = line.rstrip()
    trailing = line[len(body):]
    hard = "  " if body and re.fullmatch(r" {2,}", trailing) else ""   # keep a Markdown hard break
    pre = PREFIX.match(body).group(1)
    return body, pre, body[len(pre):], hard


def needs_wrap(plain):
    parts = PROT.split(plain)
    return bool(AR.search("".join(parts[0::2])) or INLINE.search(plain))


def _fix_line_raw(line):
    body, pre, c, hard = split_line(line)
    plain = CTRL.sub("", c)
    if not plain.strip() or not needs_wrap(plain) or not dollars_balanced(plain):
        if plain.strip() and plain == c:                  # no Arabic here, but bold markup still goes
            return pre + strip_emphasis(c) + hard
        return body + hard
    return pre + RLM + RLI + fix_content(c) + PDI + hard


SAFETY_CODES = {"bare-latin-or-digit", "math-isolate", "latin-not-upright", "line-wrap", "edge-operator"}


def fix_line(line):
    """Safety net: a line is only rewritten when the result is stable (a second pass changes
    nothing) and passes the structural checks. Otherwise it is left as it was and check reports it."""
    new = _fix_line_raw(line)
    if new == line:
        return new
    if _fix_line_raw(new) != new or SAFETY_CODES & set(check_line(new)):
        return line.rstrip() + (line[len(line.rstrip()):] if re.fullmatch(r" {2,}", line[len(line.rstrip()):]) else "")
    return new


def check_line(line):
    iss = []
    body = QUOTE.sub("", line)
    if re.match(r"\s*\|", body):
        iss.append("table")
    if HINDI_RE.search(line):
        iss.append("hindi-digits")
    _, pre, c, _ = split_line(line)
    plain = CTRL.sub("", c)
    if plain.strip() and not dollars_balanced(plain):
        iss.append("unbalanced-dollar")
    if not plain.strip() or not needs_wrap(plain):
        if plain.strip() and strip_emphasis(plain) != plain:
            iss.append("bold-markup-not-wanted")
        return sorted(set(iss))
    if not (c.startswith(RLM + RLI) and c.endswith(PDI)):
        iss.append("line-wrap")
        inner = c
    else:
        inner = c[2:-1]
    if strip_emphasis(CTRL.sub("", inner)) != CTRL.sub("", inner):
        iss.append("bold-markup-not-wanted")
    parts = PROT.split(inner)
    for i, p in enumerate(parts):
        if i % 2 == 0:
            t = CTRL.sub("", p)
            if re.search("[A-Za-z0-9]", t):
                iss.append("bare-latin-or-digit")
            if "**" in t:
                iss.append("bold-markup-not-wanted")
        elif EMPH_TAG.fullmatch(p):
            iss.append("bold-markup-not-wanted")
        elif p.startswith("$"):
            if not (parts[i - 1].endswith(LRI) and parts[i + 1].startswith(PDI)):
                iss.append("math-isolate")
            lead, core, trail = split_edges(p[1:-1])
            if lead or trail:
                iss.append("edge-operator")
            elif norm_math_token(p) != p:
                iss.append("latin-not-upright")
    return sorted(set(iss))


# ---------------------------------------------------------------- block structure
def _closes(bl, ch, size):
    s = bl.strip()
    return len(s) >= size and set(s) == {ch}


def split_row(line):
    """Cells of a table row; pipes inside code, math, wikilinks or escaped stay in the cell."""
    held = []

    def hold(m):
        held.append(m.group(0))
        return "\x00%d\x00" % (len(held) - 1)

    t = PROT.sub(hold, line.strip())
    cells = re.split(r"(?<!\\)\|", t)
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    cells = [c.replace("\\|", "|") for c in cells]
    return [re.sub("\x00(\\d+)\x00", lambda m: held[int(m.group(1))], c).strip() for c in cells]


def qsplit(line):
    """(quote prefix, rest) of a line; the prefix is '' when the line is not in a quote."""
    m = QUOTE.match(line)
    return (m.group(0), line[m.end():]) if m else ("", line)


def _table_at(lines, i):
    """Index after a table that starts at line i (header row, delimiter row, body rows), or None."""
    n = len(lines)
    if i + 1 >= n:
        return None
    p0, r0 = qsplit(lines[i])
    p1, r1 = qsplit(lines[i + 1])
    if (p0.count(">") != p1.count(">") or "|" not in r0 or "|" not in r1 or not DELIM.match(r1)
            or len(split_row(r0)) != len(split_row(r1))):
        return None
    k = i + 2
    while k < n:
        p, r = qsplit(lines[k])
        if p.count(">") != p0.count(">") or not r.strip() or "|" not in r or FENCE.match(r):
            break
        k += 1
    return k


def segments(lines):
    """Split a file into ('front'|'fence'|'display'|'unclosed'|'table'|'code'|'line', first, last)."""
    n, i, segs = len(lines), 0, []
    in_list = False
    if n and lines[0].strip() == "---":
        j = next((k for k in range(1, n) if lines[k].strip() == "---"), None)
        if j is not None:
            segs.append(("front", 0, j))
            i = j + 1
    while i < n:
        ln = lines[i]
        bl = QUOTE.sub("", ln)
        m = FENCE.match(bl)
        if m:
            ch, size = m.group(1)[0], len(m.group(1))
            k = i + 1
            while k < n and not _closes(QUOTE.sub("", lines[k]), ch, size):
                k += 1
            k = min(k, n - 1)
            segs.append(("fence", i, k))
            i = k + 1
            continue
        bs = bl.strip()
        if bs.startswith("$$"):
            if bs.count("$$") >= 2:
                if not bs[bs.rfind("$$") + 2:].strip():
                    segs.append(("display", i, i))
                    i += 1
                    continue
            else:
                k = next((k for k in range(i + 1, n) if "$$" in QUOTE.sub("", lines[k])), None)
                if k is None:
                    segs.append(("unclosed", i, n - 1))
                    i = n
                    continue
                segs.append(("display", i, k))
                i = k + 1
                continue
        end = _table_at(lines, i)
        if end:
            segs.append(("table", i, end - 1))
            i = end
            continue
        # an indented block after a blank line, outside any list, is code (CommonMark)
        if (ln[:4] == "    " or ln[:1] == "\t") and ln.strip() and not in_list and (i == 0 or not lines[i - 1].strip()):
            k = i
            while k + 1 < n:
                nxt = k + 1
                while nxt < n and not lines[nxt].strip():
                    nxt += 1
                if nxt < n and (lines[nxt][:4] == "    " or lines[nxt][:1] == "\t"):
                    k = nxt
                else:
                    break
            segs.append(("code", i, k))
            i = k + 1
            continue
        if ln.strip():
            if LISTLINE.match(ln) and not QUOTE.match(ln):
                in_list = True
            elif ln[:1] not in (" ", "\t") or (ln[:4] != "    " and ln[:1] != "\t" and not in_list):
                in_list = False
        segs.append(("line", i, i))
        i += 1
    return segs


def table_to_list(tlines):
    head = split_row(tlines[0])
    rows = [split_row(l) for l in tlines[2:]]
    if not rows:
        return ["- " + " , ".join(h for h in head if h)]
    out = []
    for r in rows:
        r = r + [""] * (len(head) - len(r))
        out.append("- " + (r[0] or head[0] or "\u2026"))
        for j in range(1, len(r)):
            if not r[j]:
                continue
            h = head[j] if j < len(head) else ""
            out.append("  - " + (h + ": " + r[j] if h else r[j]))
    return out


def fix_display(block):
    """Display math: no direction characters, ASCII digits, upright Latin. Lines stay 1:1."""
    txt = CTRL.sub("", "\n".join(block)).translate(HINDI)
    a, z = txt.find("$$"), txt.rfind("$$")
    if z <= a:
        return list(block)
    try:
        inner = upright_latin(txt[a + 2:z])
    except ValueError:
        return list(block)
    return (txt[:a + 2] + inner + txt[z:]).split("\n")


def fix_text(text, keep_tables=False, keep_rules=False):
    lines = text.split("\n")
    out, stats, skip_blank = [], {"lines": 0, "tables": 0, "rules": 0}, False
    for kind, i, k in segments(lines):
        if kind in ("front", "fence", "unclosed", "code"):
            out.extend(lines[i:k + 1])
            skip_blank = False
        elif kind == "display":
            new = fix_display(lines[i:k + 1])
            stats["lines"] += sum(1 for a, b in zip(new, lines[i:k + 1]) if a != b)
            out.extend(new)
            skip_blank = False
        elif kind == "table":
            if keep_tables:
                out.extend(lines[i:k + 1])
            else:
                qp = qsplit(lines[i])[0]
                out.extend(fix_line(qp + l) for l in table_to_list([qsplit(l)[1] for l in lines[i:k + 1]]))
                stats["tables"] += 1
                stats["lines"] += k - i + 1
            skip_blank = False
        else:
            ln = lines[i]
            s = ln.strip()
            if not keep_rules and RULE.fullmatch(s) and (not out or not out[-1].strip()):
                stats["rules"] += 1
                skip_blank = True
                continue
            if skip_blank and not s:
                skip_blank = False
                continue
            skip_blank = False
            new = fix_line(ln)
            if new != ln:
                stats["lines"] += 1
            out.append(new)
    return "\n".join(out), stats


# ---------------------------------------------------------------- checks
def clean(line):
    return CTRL.sub("", PREFIX.sub("", line, 1)).strip()


def tokens(text):
    t = re.sub(r"\\[A-Za-z]+", " ", text)
    return set(re.findall(r"[A-Za-z]+", t))


def strip_noise(block):
    """Drop what needs no key: environment names, text arguments, units after a thin space, d."""
    b = re.sub(r"\\(?:begin|end)\{[A-Za-z*]+\}", " ", block)
    b = re.sub(r"\\(?:text|textbf|textit|textrm|operatorname|mbox)\{[^{}]*\}", " ", b)
    b = re.sub(r"\\[ ,] *\\mathrm\{(?:[^{}]|\{[^{}]*\})*\}", " ", b)
    b = re.sub(r"\bd(?=\\vec)", " ", b)
    return b


GREEK = ("alpha beta gamma delta epsilon varepsilon zeta eta theta vartheta iota kappa lambda mu nu xi pi "
         "varpi rho varrho sigma varsigma tau upsilon phi varphi chi psi omega Gamma Delta Theta Lambda Xi "
         "Pi Sigma Upsilon Phi Psi Omega").split()
GREEK_RE = re.compile(r"\\(%s)(?![A-Za-z])" % "|".join(sorted(GREEK, key=len, reverse=True)))
KEYFMT = re.compile(r"^(\$[^$]+\$(?:\s*[,\u060c/]\s*\$[^$]+\$)*)\s*:\s*(\S.*)$")


def check_display(lines, i, k):
    txt = "\n".join(lines[i:k + 1])
    a, z = txt.find("$$"), txt.rfind("$$")
    inner = txt[a + 2:z]
    iss = []
    if r"\hline" in inner:
        iss.append((i + 1, "hline-in-display"))
    if CTRL.search(txt):
        iss.append((i + 1, "direction-chars-in-display"))
    if HINDI_RE.search(txt):
        iss.append((i + 1, "hindi-digits"))
    try:
        if upright_latin(inner) != inner:
            iss.append((i + 1, "display-latin-not-upright"))
    except ValueError:
        iss.append((i + 1, "display-braces-unbalanced"))
    return iss


def display_key_check(lines, segs):
    """After every $$ block: the line KEY, then one bullet per symbol of that block."""
    issues, warns, n = [], [], len(lines)
    for kind, i, k in segs:
        if kind != "display":
            continue
        block = " ".join(CTRL.sub("", l) for l in lines[i:k + 1])
        j = k + 1
        while j < n and not lines[j].strip():
            j += 1
        nxt = clean(lines[j]) if j < n else ""
        if nxt.startswith(HAYTH):
            issues.append((i + 1, "old-hayth-style-use-key"))
            continue
        if nxt != KEY:
            issues.append((i + 1, "no-key-after-display"))
            continue
        j += 1
        bullets, prev = [], j - 1
        while True:
            m = j
            while m < n and not lines[m].strip():
                m += 1
            if m < n and BULLET.match(lines[m]) and (not bullets or m == prev + 1 or KEYFMT.match(clean(lines[m]))):
                bullets.append((m, clean(lines[m])))
                prev, j = m, m + 1
                continue
            break
        if not bullets:
            issues.append((i + 1, "empty-key"))
            continue
        syms = []
        for m, text in bullets:
            f = KEYFMT.match(text)
            if not f or not AR.search(f.group(2)):
                issues.append((m + 1, "key-bullet-format"))
                continue
            syms.append(f.group(1))
            if len(f.group(2).split()) > 14:
                warns.append((m + 1, "key definition is long (keep it to a few words)"))
        m = j
        while m < n and not lines[m].strip():
            m += 1
        if m < n and LISTLINE.match(QUOTE.sub("", lines[m])):
            issues.append((m + 1, "list-after-key-needs-lead-in"))
        keytext = " ".join(INLINE.findall(" ".join(syms)))
        have = tokens(keytext)
        # the differential needs no key: d, and dx / dt when x / t is in the key
        missing = {m for m in tokens(strip_noise(block)) - have
                   if not (m == "d" or (len(m) == 2 and m[0] == "d" and m[1] in have))}
        if missing:
            warns.append((i + 1, "equation symbols missing from its key: " + ", ".join(sorted(missing)[:8])))
        gm = sorted(set(GREEK_RE.findall(block)) - set(GREEK_RE.findall(keytext)))
        if gm:
            warns.append((i + 1, "Greek letters missing from its key: " + ", ".join("\\" + g for g in gm[:8])))
    return issues, warns


def top_defs_heading(lines, segs):
    out = []
    for kind, i, _ in segs:
        if kind != "line":
            continue
        m = re.match(r"#{1,6}\s+(.*)", CTRL.sub("", lines[i]).strip())
        if m and ("\u062a\u0639\u0631\u064a\u0641" in m.group(1) or "\u0645\u0641\u0627\u062a\u064a\u062d" in m.group(1)):
            out.append((i + 1, "top-symbol-list-not-wanted"))
    return out


SOLUTION_REQ = ["فكرة السؤال", "المعطيات", "المطلوب", "الحل بالتفصيل", "التحقق من الحل", "الإجابة النهائية"]
SOLUTION_OPT = "لماذا باقي الاختيارات خاطئة"


def solution_warns(lines, segs):
    """Worked-solution files (detected by '## السؤال ...' headings) follow a fixed section order."""
    heads = []
    for kind, i, _ in segs:
        if kind != "line":
            continue
        m = re.match(r"(#{1,6})\s+(.*)", CTRL.sub("", lines[i]).strip())
        if m:
            heads.append((i + 1, len(m.group(1)), m.group(2).replace("$", "").strip()))
    qs = [h for h in heads if h[1] == 2 and h[2].startswith("السؤال")]
    if not qs:
        return []
    warns = []
    for qi, q in enumerate(qs):
        end = next((h[0] for h in heads if h[1] <= 2 and h[0] > q[0]), 10 ** 9)
        sub = [h for h in heads if q[0] < h[0] < end and h[1] == 3]
        pos = {}
        for idx, h in enumerate(sub):
            for name in SOLUTION_REQ + [SOLUTION_OPT]:
                if h[2].startswith(name) and name not in pos:
                    pos[name] = idx
        label = q[2][:30]
        for name in SOLUTION_REQ:
            if name not in pos:
                warns.append((q[0], "question «%s»: missing section «%s»" % (label, name)))
        order = [pos[nm] for nm in SOLUTION_REQ if nm in pos]
        if order != sorted(order):
            warns.append((q[0], "question «%s»: sections are out of the expected order" % label))
        if "الحل بالتفصيل" in pos:
            s0 = sub[pos["الحل بالتفصيل"]][0]
            s1 = next((h[0] for h in heads if h[1] <= 3 and h[0] > s0), end)
            if not any(h[1] == 4 and h[2].startswith("الخطوة") and s0 < h[0] < s1 for h in heads):
                warns.append((s0, "question «%s»: the detailed solution has no numbered steps (#### الخطوة ...)" % label))
    if not any(h[1] == 2 and ("ملخص" in h[2] or "الإجابات النهائية" in h[2]) for h in heads):
        warns.append((qs[-1][0], "no final summary of answers (## ملخص ...)"))
    return warns


def check_text(text):
    lines = text.split("\n")
    segs = segments(lines)
    issues, warns = [], []
    for kind, i, k in segs:
        if kind == "unclosed":
            issues.append((i + 1, "unclosed-display"))
        elif kind == "display":
            issues.extend(check_display(lines, i, k))
        elif kind == "table":
            issues.extend((j + 1, "table") for j in range(i, k + 1))
        elif kind == "line":
            ln = lines[i]
            issues.extend((i + 1, c) for c in check_line(ln))
            if RULE.fullmatch(ln.strip()) and (i == 0 or not lines[i - 1].strip()):
                issues.append((i + 1, "horizontal-rule"))
    di, dw = display_key_check(lines, segs)
    issues.extend(di)
    warns.extend(dw)
    issues.extend(top_defs_heading(lines, segs))
    warns.extend(solution_warns(lines, segs))
    return issues, sorted(warns)


# ---------------------------------------------------------------- files and CLI
def looks_like_arabic_text(p):
    try:
        if p.name.startswith(".") or p.stat().st_size > 5 * 1024 * 1024:
            return False
        raw = p.read_bytes()
        if b"\x00" in raw:
            return False
        return bool(AR.search(raw.decode("utf-8-sig")))
    except (OSError, UnicodeDecodeError):
        return False


def collect(paths):
    files = []
    for p in paths:
        P = pathlib.Path(p)
        if P.is_dir():
            for root, dirs, names in os.walk(P):
                dirs[:] = sorted(d for d in dirs if not d.startswith("."))
                files.extend(q for q in (pathlib.Path(root) / nm for nm in sorted(names)) if looks_like_arabic_text(q))
        else:
            files.append(P)
    return files


def read_text(p):
    raw = p.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    crlf = "\r\n" in text
    return (text.replace("\r\n", "\n") if crlf else text), bom, crlf


def write_text(p, text, bom, crlf):
    data = (text.replace("\n", "\r\n") if crlf else text).encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, p)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


VIS = {RLM: "<RLM>", RLI: "<RLI>", LRI: "<LRI>", PDI: "<PDI>"}


def visible(s):
    return "".join(VIS.get(c, c) for c in s)


SCAFFOLD = """## السؤال {n}: عنوان قصير

### فكرة السؤال بكلمات بسيطة

### المعطيات

### المطلوب

### الحل بالتفصيل

#### الخطوة 1:

### لماذا باقي الاختيارات خاطئة

### التحقق من الحل

### الإجابة النهائية
"""


def scaffold(n):
    body = "\n".join(SCAFFOLD.format(n=i) for i in range(1, n + 1))
    return body + "\n## ملخص الإجابات النهائية\n\n" + "".join("%d. \n" % i for i in range(1, n + 1))


def report(name, issues, warns):
    bad = bool(issues)
    if issues:
        kinds = {}
        for ln, code in issues:
            kinds.setdefault(code, []).append(ln)
        for code, lns in kinds.items():
            print("\u2718 %s: %s x%d lines %s" % (name, code, len(lns), lns[:8]))
    for ln, msg in warns:
        print("\u26a0 %s: line %d: %s" % (name, ln, msg))
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rtlmd", description="Bidi-safe Arabic Markdown with LaTeX.")
    ap.add_argument("--version", action="version", version="rtlmd " + __version__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fix", help="rewrite files (idempotent)")
    f.add_argument("paths", nargs="+")
    f.add_argument("-o", "--out", help="write the result here (one input file only)")
    f.add_argument("--diff", action="store_true", help="show the changes and write nothing")
    f.add_argument("--keep-tables", action="store_true", help="do not convert tables to lists")
    f.add_argument("--keep-rules", action="store_true", help="do not remove horizontal rules")
    c = sub.add_parser("check", help="report what is still wrong")
    c.add_argument("paths", nargs="+")
    c.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    s = sub.add_parser("scaffold", help="print an empty worked-solution skeleton")
    s.add_argument("n", nargs="?", type=int, default=1)
    a = ap.parse_args(argv)

    if a.cmd == "scaffold":
        sys.stdout.write(scaffold(max(1, a.n)))
        return 0
    files = collect(a.paths)
    if not files:
        print("\u2718 no files found")
        return 2
    if a.cmd == "fix" and a.out and len(files) != 1:
        print("\u2718 -o works with exactly one input file")
        return 2
    changed = bad = errors = 0
    for p in files:
        try:
            text, bom, crlf = read_text(p)
        except (OSError, UnicodeDecodeError) as e:
            print("\u2718 %s: cannot read (%s)" % (p, type(e).__name__))
            errors += 1
            continue
        if a.cmd == "fix":
            new, st = fix_text(text, a.keep_tables, a.keep_rules)
            if a.diff:
                if new != text:
                    changed += 1
                    sys.stdout.writelines(difflib.unified_diff(
                        visible(text).splitlines(True), visible(new).splitlines(True), str(p), str(p) + " (fixed)", n=0))
                else:
                    print("\u2714 %s: no changes" % p)
                continue
            dst = pathlib.Path(a.out) if a.out else p
            if new != text or dst != p:
                write_text(dst, new, bom, crlf)
            changed += new != text
            extra = "".join(", %s %d" % (k, st[k]) for k in ("tables", "rules") if st[k])
            print("\u2714 %s: fixed %d lines%s" % (dst, st["lines"], extra) if new != text else "\u2714 %s: no changes" % dst)
            text = new
        issues, warns = check_text(text)
        shown = dst if a.cmd == "fix" and not a.diff else p
        has = report(str(shown), issues, warns)
        if has or (a.cmd == "check" and getattr(a, "strict", False) and warns):
            bad += 1
        if not issues and not warns and a.cmd == "check":
            print("\u2714 %s ok" % shown)
        elif not issues and a.cmd == "fix":
            print("\u2714 %s ok" % shown)
    if len(files) > 1:
        print("\u2014 %d files, %d changed, %d with issues" % (len(files), changed, bad))
    return 2 if errors else (1 if bad else 0)


if __name__ == "__main__":
    sys.exit(main())
