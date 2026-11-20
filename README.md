# arabic-latex-markdown

أداة ومهارة (Claude skill) لكتابة ملفات Markdown عربية تحتوي معادلات LaTeX وكلمات إنجليزية وأرقاماً، بحيث تظهر بشكل صحيح في المحررات من اليمين إلى اليسار مثل Obsidian: الأقواس لا تنقلب، وعلامة `=` لا تقفز، والقوائم المرقمة لا تنكسر.

A Claude skill and a zero-dependency Python tool that makes Arabic Markdown with LaTeX math render correctly in RTL editors (Obsidian). Version 2.2.0.

## الاستخدام / Usage

```bash
python scripts/rtlmd.py fix   PATH      # PATH: ملف أو مجلد / file or folder
python scripts/rtlmd.py fix   PATH --diff   # معاينة فقط / preview, writes nothing
python scripts/rtlmd.py check PATH      # يفحص ويعرض الأخطاء / reports problems
python scripts/rtlmd.py scaffold 5      # هيكل حل 5 أسئلة / worked-solution skeleton
```

- `fix` يعيد الكتابة في مكانها، ولا يلمس ملفاً لم يتغير، وتشغيله مرتين لا يغيّر شيئاً.
- `check` يخرج بالرمز 1 عند أي مشكلة (وعند التحذيرات مع `--strict`).
- يحتاج Python 3.9 أو أحدث، بلا أي حزم خارجية.

القواعد كاملة وأكواد الفحص موجودة في [`SKILL.md`](SKILL.md)، والتغييرات في [`CHANGELOG.md`](CHANGELOG.md).

## استخدامه كمهارة Claude / As a Claude skill

انسخ المجلد إلى مجلد المهارات (مثلاً `~/.claude/skills/arabic-latex-markdown`) أو ارفعه كمهارة في إعدادات Claude.

## الاختبار / Tests

```bash
python scripts/test_rtlmd.py
```

أمثلة قبل/بعد في [`assets/`](assets). الأحرف الاتجاهية غير مرئية في الملفات، وهذا مقصود.

## الترخيص / License

MIT، انظر [`LICENSE`](LICENSE).
