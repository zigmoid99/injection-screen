# Limitations

This screen is a first layer, not a complete defence. Read these before relying on it.

## Detection

- **Paraphrase evasion.** Rules match vocabulary. In the labelled set, 0 of 10
  paraphrased injections were caught. Any attacker who reads `screen.py` can avoid
  every pattern.
- **English only.** Injections in other languages are not detected unless they
  happen to use English keywords.
- **No decoding.** Base64, hex, percent-encoding, HTML entities, and Unicode
  look-alikes are not normalised before matching.
- **No images, PDFs, or rendered pages.** Text hidden in images, PDF layers, or
  rendered-but-not-visible elements is only seen if it appears in the input string.
- **Comment and CSS checks are shallow.** Instructions split across comments,
  attributes, or script blocks will not be seen.

## Accuracy

- **False positives on ordinary text.** 5 of 21 benign sentences were flagged in
  the labelled set (24%). Common causes are broad verb patterns and the
  line-start `System:` rule.
- **The labelled set is small and was written by the rule author.** The numbers in
  `docs/PAPER.md` measure this implementation on this set. They are not an
  estimate of performance on real traffic.
- **Thresholds were set by inspection**, not fitted to data.

## Handling

- **The wrapper is advisory.** A model can still follow instructions inside a
  `flag`-level wrapper. The wrapper makes the boundary explicit; it does not enforce it.
- **Block withholds, it does not sanitise.** Withheld content is replaced by a
  placeholder. The screen does not attempt to remove just the injected part.
- **No logging is built in.** Callers are responsible for recording verdicts and
  signal names if they want an audit trail.

## Scope

- **Not a model safety control.** Screening input does not stop a model from
  producing harmful output or from being persuaded by content that passes the screen.
- **Capability limits matter more.** If an injected model can send email, move money,
  or run commands without a check, no input screen is adequate on its own.
