# Limitations

This screen and gate are a first layer, not a complete defence. Read these before relying on them.

## Detection

- **Paraphrase evasion.** Rules match vocabulary. In the dev set, 0 of 10 paraphrased
  injections were caught by the screen. Anyone who reads `screen.py` can avoid
  every pattern. The taint gate is the mitigation, not the screen.
- **English only.** Injections in other languages are not detected unless they use
  English keywords.
- **Normalisation is small.** The look-alike table covers a handful of Cyrillic and
  Greek letters, not a full confusables set. Other encodings (for example
  quoted-printable, UTF-7, nested encodings) are not decoded.
- **Hidden-text parsing is heuristic.** It reads inline `style` attributes and a few
  attributes. External stylesheets, scripts that write text at runtime, and
  rendered layout (for example, text covered by an image) are not seen.
- **No images, PDFs, or rendered pages.** Text inside images or PDF layers is only
  seen if it appears in the input string.
- **Addressed-to-AI rule is partial.** It missed 1 of 5 injected phrasings in the
  dev set, and flagged 1 of 5 benign sentences ("When you summarize this report…").

## Accuracy

- **False positives on ordinary text.** On the dev set: 5 of 21 v0.1 benign sentences
  flagged (24%), and 1 of 5 addressed-to-AI benign sentences flagged (20%). Common
  causes are broad verb patterns, the line-start `System:` rule, and words
  addressed to a model that also appear in ordinary instructions.
- **All labelled data is dev data.** The test sets were written by the rule author,
  who also fixed one look-alike gap after seeing it. The numbers measure this
  implementation on these sets. They are not an estimate of performance on real
  traffic, and they are not held-out.
- **Thresholds, trust levels and tool risk tiers were set by judgement**, not fitted.

## Gate

- **Protection depends on the tool risk tiers.** A high-risk action classified as
  low risk is allowed in every session. Unknown tools are treated as high risk.
- **Protection depends on the approver.** A reviewer who approves every request
  removes the control. The default with no approver is deny.
- **Taint is sticky for the session.** Once untrusted content has entered, high-risk
  actions need approval for the rest of the session. This is intended, but it adds
  friction, and the gate does not reduce the taint after the content is gone.
- **Taint is per session, not per data flow.** The gate does not track which
  untrusted text influenced which tool argument. A session that read a page is
  treated as tainted as a whole.
- **Arguments are not inspected.** The gate decides on tool name and taint. It does
  not check whether an email's recipient came from the untrusted text.
- **The gate was demonstrated, not benchmarked.** `make gate-demo` is a scripted
  scenario with no model.

## Handling

- **The wrapper is advisory.** A model can still follow instructions inside a
  `flag`-level wrapper. The wrapper makes the boundary explicit; it does not enforce it.
- **Block withholds, it does not sanitise.** Withheld content is replaced by a
  placeholder. The screen does not remove only the injected part.
- **Logging is the caller's responsibility.** The gate keeps an in-memory audit list.
  Persisting it is up to the application.

## Scope

- **Not a model safety control.** Screening input does not stop a model from producing
  harmful output or from being persuaded by content that passes the screen.
- **Capability limits matter most.** If an injected model can send email, move money
  or run commands without a check, the screen alone is not adequate. The gate helps,
  but only where the application routes tool calls through it.
