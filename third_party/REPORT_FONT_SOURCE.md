# PaperLens selectable report font

The privately seeded `PaperLens-Report-Regular.ttf` is a modified OFL font,
renamed **PaperLens Report Regular**, weight 400. The pinned byte count,
SHA256 and all original font URLs/hashes are in `website/seed/report-font.json`.
The full font is deliberately absent from the repository and Worker bundle.

Sources are the official Google Fonts Noto Sans SC variable TTF, Noto Sans
variable TTF, and Noto Sans Math Regular TTF. Their unmodified OFL notices are
retained beside this file. No license or original copyright notices were
removed from font metadata. The modified family name avoids using a source
family name for the derived font.

Preparation used fontTools 4.61.1. Instantiate Noto Sans SC at `wght=400` and
Noto Sans at `wght=400, wdth=100`; keep SC's original horizontal glyphs and
append missing Latin/Greek/punctuation/math/subscript code points from Noto
Sans, followed by remaining Noto Sans Math code points. Composite supplement
outlines are decomposed and scaled to SC's units per em. Copy scaled horizontal
metrics and add base vertical fallback metrics for appended glyphs. Update all
Unicode cmap subtables and glyph order; change family/name IDs to PaperLens
Report Regular. Remove GSUB from the report font: fontkit's default numeric
alternates can otherwise draw correctly but extract as an unrelated Unicode
character in the pinned PDF library. Literal cmap mapping preserves report
digits and supplementary Unicode during selection. The required-glyph check covers Chinese, Latin, Greek,
chemical subscripts, superscripts, minus, approximate sign and common math.

The output has 34,423 Unicode characters and is below 12 MiB. It does not
claim every Unicode or emoji glyph. The renderer rejects unsupported code
points with a concrete U+ error instead of silently drawing replacement boxes.
PDFs embed one compressed static font, retain selectable Unicode text, and
make no external font/model request. Runtime fontkit subsetting was disabled
after actual MuPDF rasterization showed missing outlines despite complete
selectable text. The five-paper PDF with the complete compressed font remains
below 12 MiB. The font is never placed inside Worker JavaScript. The
authenticated same-origin font route serves the pinned original bytes from
private object storage.

Full source fonts, preparation scripts and final font remain under ignored
`/workspace/work/batch-development/`; the final artifact is
`PaperLens-Report-Regular.ttf`. Those local paths are development artifacts,
not public download URLs.

Public CI font is a local FontTools subset of the same static production font, using only public UI/test strings (not paper text). Reproduce with website/scripts/build-ci-report-font.py. SHA256: a4014930633f87ed13c6c0a1c3068b90ffc8e1a4f5f7f6ad02c516fb83c51785; bytes: 330428. Production font remains separately hash-pinned in website/seed/report-font.json and stored only in private R2.

Revision 2 (2026-11-19): private full font PaperLens-Report-Regular-v2.ttf adds 1,483 remaining NotoSans weight-400 glyphs, including U+02DC small tilde. Bytes 11,175,960; SHA256 0b25a1253476f100644b396da442f4633c3d4982123b121a51c36519b380b6da. The prior pinned font is retained; the new font uses a new immutable R2 hash and browser revision URL. No original Unicode text was rewritten.

Updated public CI-only subset: 331,072 bytes; SHA256 21ccaa853232e5f8d295c03a285e23e4266b5ab8b7d91f8fb87ebea7e28d82ab; 2,006 characters derived only from public interface/engineering fixture strings.

2026-11-20: the public CI subset now also scans public report/test module strings for the Chinese-first renderer. It remains derived only from public code and explicitly synthetic fixtures; no real paper or private Chinese guide is included. Current subset: 333388 bytes, SHA256 294e2a7af7731cf377e4515e49d3181e7339f791428e7215e4eb020a07428899. The full private v2 report font is unchanged.
