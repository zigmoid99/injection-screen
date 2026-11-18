# Changelog

All notable changes to injscreen are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

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
