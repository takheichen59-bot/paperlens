# One real paper: actual rule extraction and export

Source: [BiFeO$_3$ nanoparticles at low-temperature using atomistic simulations -- surface charge distribution and terminations](https://arxiv.org/abs/2501.00680v1). Authors: Mauro A. P. Goncalves, Monica Graf, Marek Pasciak, Jiri Hlinka. Version2501.00680v1,11 pages, CC BY4.0. PDF SHA256 `1f88d96cfa8bc36595ac00eaebd42db85fbcc1eb35733058e2399906aa0fb7cd`.

This uses the actual official PDF downloaded previously; its bytes were reverified for this export. It is not a synthetic fixture, not claimed as a new download and not an independent scientific-accuracy evaluation.

## Observed automatic output

| Field | Actual result | Evidence |
|---|---|---|
| Materials | BiFeO3; MoS2; Bi4Ti3O12 | BiFeO3 is the modeled material. The other two are background comparisons on page2, **not modeled samples**. Automatic output is retained unchanged. |
| Methods | 1676 characters | Pages3–4; shell-model classical molecular dynamics, DL_POLY,1K,10ps thermalization plus10ps averaging. |
| Findings | 134 characters; one source sentence | Page8, block p8-b4, offsets167:301. |
| Conclusions | 405 characters | Page8; multiple polarization configurations and a stripe-like arrangement under neutral terminations. |
| Evidence | 22 snippets | Every text equals its raw block slice. |
| Review | unreviewed | status=success describes legacy field/evidence structure, not scientific truth. |

Exact finding:

> We observed various polarization arrangements, ranging from a homogeneous monodomain to complex configurations with vortex formations.

## Small fix prompted by this paper

The previous findings expression recognized `We observe` but missed `We observed`. Added bounded past/perfect variants of observe/show/find, retaining original text, offsets and negation. The sentence above was absent before and present after; methods/conclusions/material candidates were unchanged. Bumped the scientific extractor version to `scientific-evidence-v1.1` so existing hash/version checkpoints do not silently reuse the old result.

`tests/master/test_finding_tenses.py`:3 PDF integration tests cover past/perfect variants, exact raw evidence, preservation of a negative finding, and the tested future/reference exclusions. This remains a keyword baseline, not semantic claim validation or deep algorithm extraction.

## Export verification

The generated workbook has one paper row; its method/finding/conclusion cell contents match JSONL. All22 raw snippet slices match; the original PDF SHA matches the verified corpus. The preview was opened through a real Chromium loopback session and an actual Excel download event was checked. This does not validate rendering in Microsoft Excel itself.

The delivered sample contains original PDF, automatic Excel/CSV/JSONL, raw evidence CSV, a separate assistant reading guide and checksums. The reading guide flags background-material and background-numeric candidates; it does not rewrite the automatic record or mark it human-reviewed. The PDF cache and full export package are **not committed to Git**.

Reproduce core exports with a legal local PDF and manifest:

```bash
python -m research run --manifest manifest.json --workdir work/one-paper --output work/one-paper-output --workers 1
```

Manifest example: `[{"meta": {"paper_id":"arxiv:2501.00680","id":"2501.00680v1","title":"BiFeO3 nanoparticles at low-temperature using atomistic simulations","url":"https://arxiv.org/abs/2501.00680v1","doi":null}, "pdf":"paper.pdf"}]`.

Remaining issues: background-material role classification, background numeric candidates and incomplete findings coverage. No real NER/LLM service was called; no precision/recall is asserted.
