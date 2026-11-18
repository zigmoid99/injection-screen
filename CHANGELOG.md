# Changelog

All notable changes to injscreen are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

## [0.2.0] — 2026-11-17

### Added
- **Normalised views** (`normalize.py`): NFKC folding, look-alike table, invisible-character
  removal, spaced-letter collapse, percent and entity decoding, base64 decoding. Rules run on
  every view; a match found only in a decoded view adds an `obfuscation` signal.
- **HTML-aware hidden text** (`htmlscan.py`): splits HTML into visible and hidden text
  (comments, invisible elements, `aria-hidden`, `alt`/`title`/`meta`). Instruction-like hidden
  text adds `hidden_instruction`, which replaces `hidden_comment_instruction`.
- **Trust levels**: `screen(text, source, trust=...)` with per-trust thresholds (`web`, `tool`,
  `upload`, `user`). `web` keeps the v0.1 thresholds.
- **Addressed-to-AI rule** `addresses_ai` (weight 2).
- **Taint-tracking gate** (`gate.py`): `TaintGate` with session taint
  (clean → untrusted → suspicious → hostile), tool-risk authorisation, approver callback,
  fail-closed on unknown tools, and an audit log that records tool names and decisions but not
  argument values.
- `examples/gate_demo.py` and `make gate-demo`.
- New dev-set categories: `html-injected`, `html-benign`, `obfuscated`, `obfuscated-benign`,
  `addressed-injected`, `addressed-benign` (31 records).
- 33 new unit tests (50 total), with pinned evaluation results for the new categories.

### Changed
- `eval` table widened for longer category names; new categories ordered after v0.1 ones.
- `docs/PAPER.md` and `docs/LIMITATIONS.md` rewritten for v0.2.

### Fixed
- Added uppercase Cyrillic `І` to the look-alike table after the obfuscation test case exposed
  the gap. Found on the dev set, so this is not an independent measurement.

### Known issues
- 0 of 10 paraphrased injections detected by the screen (the gate is the mitigation)
- 5 of 21 v0.1 benign records flagged (24%); 1 of 5 addressed-to-AI benign records flagged
- 1 of 5 addressed-to-AI injected records missed
- All labelled data is dev data written by the rule author

## [0.1.0] — 2026-11-17

### Added
- Weighted rule screen for indirect prompt injection (11 rules, 2 structural checks)
- Verdicts `allow` / `flag` / `block` with a wrapper that labels flagged content as data
- `injscreen check` and `injscreen eval` CLI
- Labelled test set: 21 benign, 12 direct, 10 indirect, 10 paraphrased
- 17 unit tests with pinned evaluation results
- `docs/PAPER.md` and `docs/LIMITATIONS.md`

### Known issues
- 0 of 10 paraphrased injections detected
- 5 of 21 benign records flagged (24%)
