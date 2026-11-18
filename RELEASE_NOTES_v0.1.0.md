# injscreen v0.1.0 — release notes

A first, deliberately simple screen for indirect prompt injection in untrusted text.

## What it does

Scores text against 11 weighted rules plus two structural checks (invisible characters, instructions inside HTML comments), then returns `allow`, `flag`, or `block`. Flagged content is wrapped and labelled as data. Blocked content is withheld.

## What it measured

On the 53-record labelled set shipped in `testdata/`:

- 100% of direct injections caught (12/12)
- 100% of indirect injections caught (10/10)
- 0% of paraphrased injections caught (0/10)
- 24% of benign records flagged (5/21), none blocked

These are in-distribution numbers for rules written after the attack examples. They are not a generalisation claim. See `docs/PAPER.md`.

## Known issues

- Paraphrase evasion is complete on the set shipped here.
- The false-positive rate on ordinary text is too high to use the flag label as a hard control.
- English only, no decoding of base64 or other encodings.

## Install and try it

```bash
make test
make eval
PYTHONPATH=src python3 -m injscreen check page.html --wrap
```
