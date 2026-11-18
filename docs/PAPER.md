# Screening Untrusted Text Before It Reaches an LLM: A Small, Honest Baseline

*Written for: engineers building LLM features that read content they did not write.*

## 1. The problem

Most useful LLM applications now read text that someone else wrote: web pages a
research agent fetches, documents a user uploads, emails an assistant triages,
tool output from an API, a customer's support ticket, a résumé in a screening
pipeline. The model cannot reliably tell the difference between the instructions
its developer wrote and the instructions that happen to be embedded in that
content. This is **indirect prompt injection**, and it is the failure mode that
matters most once a model can take actions: send an email, call a tool, read a
secret.

Direct prompt injection, where the user types "ignore your instructions", is
the familiar case, and the user is at least the party you are already talking
to. Indirect injection is harder. The attacker is absent, the payload sits in
the middle of a document that looks ordinary, and the victim is the person who
asked for a summary.

The practical question for an engineer is narrow: **before untrusted text enters
the model's context, can we cheaply notice the obvious attempts and do something
sensible about them?** This project answers that question with the smallest
thing that could work, and then measures how far it gets.

## 2. Scope and what this is not

This repository is a **screening layer**, not a defence. It is a place to:

- score text for signals that commonly appear in injection attempts,
- decide whether to allow, label, or withhold that text, and
- measure what the approach catches and misses on a labelled set.

It does not make a model safe, does not sanitise arbitrary content, and does not
replace least-privilege tool design, output filtering, or human review. Those
controls matter more than any detector, and the paper's main argument is that a
detector should be one layer among several.

## 3. Threat model

**Attacker.** Can place text where the application will read it: a web page, a
shared document, an email body, a comment in a code file, a field in a form. The
attacker does not have access to the system prompt or the tool configuration.

**Goal.** Make the model do something the application owner did not intend. The
three goals assumed here are:

1. *Override*: change the task or ignore prior instructions.
2. *Exfiltrate*: get the model to send secrets or conversation data somewhere.
3. *Act*: get the model to run a command or call a tool with attacker-chosen
   arguments.

**Out of scope.** Training-time poisoning, attacks on the model's weights,
side-channel leakage, and attacks that succeed without any instruction-like
text (for example, a manipulated number in a spreadsheet that the model
trusts). These are real but need different controls.

## 4. Approach

The screen runs in three passes over the raw text. It needs no model call, no
network access, and no dependencies beyond the Python standard library. That is a
deliberate constraint: the screen must be cheap enough to run on every input,
must work offline, and must not itself be an LLM that can be injected.

**Pass 1 — weighted pattern rules.** Eleven regular expressions, each
representing a family of phrasing that injection attempts tend to share:

| Rule | Weight | What it looks for |
|---|---|---|
| `override_instructions` | 3 | "ignore / disregard / forget … previous / all / your … instructions / rules" |
| `prompt_exfiltration` | 3 | "reveal / print / repeat … system prompt / hidden instructions" |
| `role_spoofing` | 3 | Lines starting `system:` or `assistant:`, chat template tokens such as `<\|im_start\|>` |
| `data_exfiltration` | 3 | "send / upload … password / api key / chat history … https://" |
| `dangerous_command` | 3 | `rm -rf ~`, `curl … \| sh`, `chmod 777 /` |
| `persona_hijack` | 2 | "you are now", "from now on you", "developer mode", "jailbreak" |
| `concealment` | 2 | "do not tell the user", "without the user knowing" |
| `markdown_image_beacon` | 2 | Markdown images with query strings, a common exfiltration channel |
| `execution_coercion` | 2 | "run the following command" |
| `false_authority` | 2 | "this is an administrator / system message" |
| `hidden_css` | 1 | `display:none`, `font-size:0`, `visibility:hidden` |

**Pass 2 — structural checks.** Two checks that do not depend on phrasing:

- *Invisible characters* (zero-width spaces, bidirectional overrides). These are
  rarely present in ordinary prose and are a common way to hide text from a
  human reviewer while leaving it visible to a model. Weight 2.
- *Instructions inside HTML comments.* The body of each `<!-- … -->` is checked
  against the instruction-like rules. Comments are invisible when a page is
  rendered but readable to a model that receives the raw HTML. Weight 2.

**Pass 3 — verdict and handling.** Each rule counts once. The score maps to:

- `allow` (score 0–1): pass the text through unchanged.
- `flag` (score 2–3): wrap the text in a provenance tag and prepend a note that
  the content is data and its instructions should not be followed.
- `block` (score ≥ 4): withhold the text and insert a short placeholder that
  names the matched signals.

The wrapper is itself a mitigation sometimes called *spotlighting*: it does not
stop a model from being persuaded, but it makes the boundary between instruction
and data explicit in the prompt, which helps a well-behaved model and makes the
audit trail clearer. The wrapper escapes any attempt to close it from inside the
content.

## 5. Assumptions

These are the assumptions the design rests on. If one of them is false for your
application, the screen will serve you less well.

1. **Injection attempts tend to be written in recognisable English.** Attackers
   who write in another language, or who paraphrase heavily, will get past the
   rules. The rules encode common phrasings, not intent.
2. **Most attempts are not adversarially optimised against this screen.** The
   rules are public, so an attacker who reads this paper can avoid every
   pattern. The screen is most useful against opportunistic or template-based
   attacks, and against accidental instruction-like text.
3. **A false positive is cheaper than a false negative in the flag band.**
   Flagging only adds a label to the content, so over-flagging costs a little
   context. Blocking is more expensive, so the block threshold is set high.
4. **The application already limits what the model can do.** The screen assumes
   that a successful injection cannot, by itself, send money or delete data. If
   the model can take those actions unchecked, no screen is adequate.
5. **Text arrives as text.** The screen reads Unicode strings. Content hidden in
   images, PDFs with unusual encodings, or base64 blobs is not decoded. This is
   listed as a gap below.

## 6. Considerations

**Why regular expressions and not a classifier?** A trained classifier would
likely do better on paraphrases, and it is the obvious next step. It was not the
first step because (a) it adds a model dependency that is itself injectable,
(b) its failures are harder to explain to a reviewer, and (c) a rule set can be
read, argued with, and changed in an afternoon. A classifier should be evaluated
against exactly the same labelled set before replacing or augmenting these
rules.

**Why weights and thresholds rather than a single match means block?** Several
rules are noisy on their own. `persona_hijack` fires on "you are now subscribed".
`role_spoofing` fires on a log line that begins `System:`. Weights let a single
weak signal produce a label without withholding content, while stacked signals
produce a block. The thresholds were set by inspection, not optimised, and that is
stated plainly in the results.

**Where should the screen sit?** At the boundary where untrusted content enters
the prompt, not inside the model. Every tool result, retrieved document and user
upload that is not written by the developer should pass through `screen` and
`wrap`. Developer-written system prompts and trusted configuration should not.

**What to log.** The `Result` object carries the source, score, verdict and
signal names. Logging these, without logging the full content, gives an audit
trail for "why did the agent refuse to read this page" and lets you measure the
false-positive rate in your own traffic.

**Maintenance.** Rules will drift as phrasing changes. The labelled set in
`testdata/` is the regression harness. Any rule change should re-run
`make eval`, and the pinned numbers in `tests/test_screen.py` should be updated
together with this paper.

## 7. Evaluation

The labelled set has 53 records in four categories: 21 benign, 12 direct
injections, 10 indirect injections (embedded in otherwise ordinary content), and
10 paraphrased injections written to avoid the rule vocabulary. The benign set
includes deliberately tricky ordinary sentences such as "ignore the
`.DS_Store` files", "you are now subscribed", and "System: Ubuntu 22.04".
Results come from `make eval` at commit time and are reproduced here exactly.

| Category | Label | n | Blocked | Flagged only | Flagged or blocked | Rate |
|---|---|---|---|---|---|---|
| benign | benign | 21 | 0 | 5 | 5 | **24% false-positive rate** |
| direct | injected | 12 | 9 | 3 | 12 | **100% recall** |
| indirect | injected | 10 | 4 | 6 | 10 | **100% recall** |
| paraphrased | injected | 10 | 0 | 0 | 0 | **0% recall** |

Reading these numbers:

- **Direct and indirect injections are caught.** This is expected: the rules were
  written after looking at this exact style of attack, so this is an
  in-distribution result. It shows the implementation works. It does not show
  that the rules generalise. Treat it as a floor on what the approach can do,
  not an estimate of real-world recall.
- **The false-positive rate is high.** All five benign flags are at the `flag`
  level, so none are withheld, but a 24% rate would be unacceptable if the flag
  label changed what the model did. Two causes dominate: broad verb patterns
  (`execution_coercion` on "run the following command", `false_authority` on "this
  is an administrator-only feature") and the `role_spoofing` line-start rule. A
  fix would narrow these, but tuning them on this same set would overstate the
  improvement, so that work needs a fresh benign set.
- **Paraphrased injections are not caught at all.** This is the most important
  result. Each paraphrase carries the same intent with different words: "set aside
  the guidance you were given", "keep this between us", "treat the following as
  your new operator". The rules only see vocabulary. An attacker who knows the
  rules has an easy path around them.

Put simply: **this screen reliably catches the attacks that look like attacks,
and reliably misses the ones that have been reworded to avoid vocabulary.** For an
engineering team this is a reasonable first layer and a poor only layer.

## 8. Limitations

See [LIMITATIONS.md](LIMITATIONS.md) for the full list. The most important:

- The rules are English-only and vocabulary-based. Paraphrase is the dominant
  evasion, and the measured recall on paraphrases is zero.
- The labelled set was written by the same person who wrote the rules. It is a
  regression harness, not an independent benchmark.
- The screen does not decode base64, hex, or images, and does not follow links.
- The false-positive rate on ordinary text is substantial and has not been
  measured on real traffic.

## 9. What would come next

In rough order of value per effort:

1. **Collect a fresh benign set** from real content the application will read, and
   measure the false-positive rate there before changing any rule.
2. **Add a paraphrase set written by someone other than the rule author**, and
   treat its recall as the number to improve.
3. **Evaluate a small classifier** against the same sets, as an additional
   signal rather than a replacement, and keep it out of the trust boundary.
4. **Decode common encodings** (base64, percent-encoding, HTML entities) before
   screening, since these hide vocabulary from pattern matching.
5. **Pair the screen with capability limits**: the strongest real control is making
   sure that a model which *is* injected cannot do much harm.

## 10. Summary

Indirect prompt injection is a real and current problem for any LLM application
that reads content it did not write. A cheap, offline, rule-based screen catches
the obvious attempts and makes the trust boundary explicit in the prompt. It does
not catch reworded attempts, and it produces too many false positives to be used
alone. The useful result is not that the approach works; it is that the failure
modes are now measured, and the next step is clear.
