# Screening Untrusted Text Before It Reaches an LLM: A Small, Honest Baseline

*Written for: engineers building LLM features that read content they did not write.*

*Version 0.2.0. Results in section 7 are from the development set, which the rule
author also wrote. They measure the implementation, not generalisation.*

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

Two questions follow for an engineer. First: **before untrusted text enters the
model's context, can we cheaply notice the attempts and do something sensible
about them?** Second, and more important: **when detection misses, can we still
limit what the model is allowed to do?** This project addresses both, with the
smallest things that could work, and measures how far they get.

## 2. Scope and what this is not

This repository is a **screening and capability-limiting layer**, not a defence.
It is a place to:

- score text for signals that commonly appear in injection attempts,
- decide whether to allow, label, or withhold that text,
- track how tainted a session is after untrusted content enters it, and
- measure what each part catches and misses on a labelled set.

It does not make a model safe, does not sanitise arbitrary content, and does not
replace least-privilege tool design, output filtering, or human review. The
paper's main argument is that a detector should be one layer among several, and
that the capability gate matters more than any detector when detection fails.

## 3. Threat model

**Attacker.** Can place text where the application will read it: a web page, a
shared document, an email body, a comment in a code file, a hidden element in a
form. The attacker does not have access to the system prompt or the tool
configuration.

**Goal.** Make the model do something the application owner did not intend:

1. *Override*: change the task or ignore prior instructions.
2. *Exfiltrate*: get the model to send secrets or conversation data somewhere.
3. *Act*: get the model to run a command or call a tool with attacker-chosen
   arguments.

**Evasion.** The attacker knows the rules are public. Relevant evasions are
rewording, Unicode look-alikes and invisible characters, encodings, hiding text
from a human reader (CSS, alt text, comments), and addressing the model
indirectly ("note to any AI reading this").

**Out of scope.** Training-time poisoning, attacks on the model's weights,
side-channel leakage, and attacks that succeed without instruction-like text (for
example, a manipulated number in a spreadsheet that the model trusts).

## 4. Approach

The design has two layers. The **screen** decides what text looks like. The
**gate** decides what the session may do after it has read that text. Both use
only the Python standard library and make no model calls. That is a deliberate
constraint: the screen must run on every input, work offline, and must not itself
be an LLM that can be injected.

### 4.1 Screening rules

Twelve weighted regular expressions, each covering a family of phrasing:

| Rule | Weight | What it looks for |
|---|---|---|
| `override_instructions` | 3 | "ignore / disregard / forget … previous / all / your … instructions / rules" |
| `prompt_exfiltration` | 3 | "reveal / print / repeat … system prompt / hidden instructions" |
| `role_spoofing` | 3 | Lines starting `system:` or `assistant:`, chat template tokens |
| `data_exfiltration` | 3 | "send / upload … password / api key / chat history … https://" |
| `dangerous_command` | 3 | `rm -rf ~`, `curl … \| sh`, `chmod 777 /` |
| `persona_hijack` | 2 | "you are now", "from now on you", "developer mode", "jailbreak" |
| `concealment` | 2 | "do not tell the user", "without the user knowing" |
| `markdown_image_beacon` | 2 | Markdown images with query strings, a common exfiltration channel |
| `execution_coercion` | 2 | "run the following command" |
| `false_authority` | 2 | "this is an administrator / system message" |
| `addresses_ai` | 2 | Content that speaks to the model: "note to any AI reading this", "if you are an AI assistant", "when you summarize this" |
| `hidden_css` | 1 | `display:none`, `font-size:0`, `visibility:hidden` |

### 4.2 Normalised views (B1)

Pattern matching sees only the characters it is given. Before matching, the
screen builds several views of the text and runs every rule on each one:

- **normalized**: NFKC folding, a small table of Cyrillic and Greek look-alikes
  (for example Cyrillic `а` for Latin `a`), removal of invisible characters, and
  collapsing of spaced letters (`i g n o r e` becomes `ignore`).
- **percent** and **entity**: URL-decoded and HTML-unescaped text.
- **base64**: contiguous tokens that decode to mostly printable UTF-8.

The raw view is always checked first. A rule that matches only in a decoded view
adds an `obfuscation` signal (weight 1), so the audit trail shows that the text
was hiding something.

The look-alike table is deliberately small. It is not a confusables database,
and a letter outside the table is still a gap.

### 4.3 Hidden text (B2)

Much of the text a model sees from a web page is invisible to a human reader:
comments, elements styled out of view, `aria-hidden` content, and attribute text
such as `alt`, `title`, and `<meta content>`. For inputs that look like HTML, a
stdlib parser (`html.parser`) splits the content into visible and hidden text.
Hidden means:

- comments,
- elements with `display:none`, `visibility:hidden`, `font-size:0`, `opacity:0`,
  large negative offsets, or white text,
- elements marked `hidden` or `aria-hidden="true"` (the hidden state applies to
  the whole subtree),
- `alt`, `title`, and `<meta content>` values.

If any instruction-like rule matches the hidden text, the screen adds a
`hidden_instruction` signal (weight 2). This generalises the earlier HTML-comment
check. Instructions in hidden text are a strong sign, because a person reviewing
the page would not see them.

### 4.4 Trust levels (B3)

The same score should not mean the same thing for every source. Thresholds depend
on the trust level of the source:

| Trust | Flag at | Block at | Intent |
|---|---|---|---|
| `web` | 2 | 4 | Fetched pages, the default |
| `tool` | 2 | 3 | Tool output, often machine-generated and easy to block |
| `upload` | 2 | 3 | Third-party files |
| `user` | 4 | 6 | The user's own input, screened mainly for logs |

These values are a judgement, not fitted to data.

### 4.5 Verdict and handling

Each rule counts once. The score maps to a verdict using the thresholds above.

- `allow`: pass the text through unchanged.
- `flag`: wrap the text in a provenance tag and prepend a note that the content is
  data and its instructions should not be followed.
- `block`: withhold the text and insert a placeholder that names the matched
  signals.

The wrapper is a mitigation sometimes called *spotlighting*. It does not stop a
model from being persuaded, but it makes the boundary between instruction and data
explicit in the prompt. The wrapper escapes any attempt to close it from inside
the content.

### 4.6 The taint gate (D)

The screen will miss some attacks. Paraphrase is the case the evaluation shows
most clearly (section 7). The gate is built for that case: it limits what a
session may do after untrusted content has entered it, whether or not the screen
noticed anything.

The gate keeps a session taint that only rises:

```
clean  ->  untrusted  ->  suspicious  ->  hostile
```

- **clean**: no non-user content has been ingested.
- **untrusted**: non-user content was ingested and the screen allowed it. This is
  the important state. A paraphrased injection that passes the screen still moves
  the session here.
- **suspicious**: ingested content was flagged.
- **hostile**: ingested content was blocked.

Tool calls are authorised against the taint. Low-risk tools (search, read,
calculator) are always allowed. High-risk tools (send, write, delete, shell,
network post) are:

- allowed in a clean session,
- sent to a human approver in an untrusted or suspicious session (denied if there
  is no approver), and
- denied in a hostile session.

Unknown tools are treated as high risk, so the gate fails closed. The audit log
records tool names, decisions and taint, but never argument values or content.

`examples/gate_demo.py` shows the behaviour with a scripted agent and no model. It
reads a paraphrased poisoned page, which the screen allows, then tries to send an
email. Without the gate, the email is sent. With the gate and no approver, the
email is denied. With a human approver, it is sent. The point is that the gate
decides, not the screen.

### 4.7 Assumptions

These are the assumptions the design rests on. If one is false for your
application, the design serves you less well.

1. **Most injection attempts are not adversarially optimised against the screen.**
   The rules are public. An attacker who reads this paper can avoid every pattern.
2. **A false positive in the flag band is cheap.** Flagging adds a label and costs
   a little context. Blocking is more expensive, so the block thresholds are set
   higher.
3. **Tool risk can be classified.** The gate assumes each tool can be placed in a
   risk tier. A mis-tiered tool weakens the gate.
4. **A human can approve a high-risk action sensibly.** The approval path assumes
   the reviewer sees the tool and its arguments. An approver who rubber-stamps
   requests removes the protection.
5. **Text arrives as text or HTML.** Content in images, PDFs, or nested encodings
   is not seen.

## 5. Considerations

**Why regular expressions and not a classifier?** A trained classifier would likely
do better on paraphrases, and it is the obvious next step. It was not the first
step because (a) it adds a model dependency that is itself injectable, (b) its
failures are harder to explain to a reviewer, and (c) a rule set can be read,
argued with, and changed quickly. A classifier should be evaluated on a held-out
set before it is claimed to help.

**Why a gate, not just a better screen?** Detection is a race against rewording.
The gate does not depend on recognising the attack. It depends on knowing that
untrusted content entered the session and that some tools are dangerous. Those
are facts the application controls, which makes the gate the more reliable
control.

**Why weights and thresholds rather than a single match means block?** Several
rules are noisy on their own. `persona_hijack` fires on "you are now subscribed".
`role_spoofing` fires on a log line that begins `System:`. Weights let a single
weak signal produce a label without withholding content, while stacked signals
produce a block.

**Where should the screen sit?** At the boundary where untrusted content enters
the prompt. Every tool result, retrieved document and fetched page that the
developer did not write should pass through `TaintGate.ingest` (or `screen` and
`wrap`). Developer-written system prompts and trusted configuration should not.

**What to log.** The `Result` object and the gate's audit entries carry source,
score, verdict, signal names and tool decisions, without content. This gives an
audit trail for "why did the agent refuse this page" and lets you measure the
false-positive rate on your own traffic.

**Maintenance.** Rules will drift as phrasing changes. The labelled set in
`testdata/` is the regression harness. Any rule change should re-run `make eval`,
and the pinned numbers in `tests/test_screen.py` should be updated together with
this paper.

## 6. Evaluation method and its limits

The labelled set has 84 records in ten categories. Every record was written by the
rule author. That is the most important caveat in this paper.

The categories are:

- `benign`, `direct`, `indirect`, `paraphrased` (v0.1 set, 53 records)
- `html-injected`, `html-benign` (hidden-text cases)
- `obfuscated`, `obfuscated-benign` (normalisation cases)
- `addressed-injected`, `addressed-benign` (speaking to the model)

One change was made after looking at results. An uppercase Cyrillic `І` was added
to the look-alike table because the homoglyph test case exposed the gap. This is
a real confusable, but it was found on the same set it is measured against.
Likewise, the paraphrase set was reported as a gap, not tuned.

A held-out evaluation requires text the rule author did not see. That work is the
first item in section 9.

## 7. Results

Results from `make eval` at version 0.2.0, on the development set. "Block" and
"flag" are the verdicts. Rate is the share flagged or blocked, which is recall for
injected categories and the false-positive rate for benign categories.

| Category | Label | n | Block | Flag | Allow | Rate |
|---|---|---|---|---|---|---|
| benign | benign | 21 | 0 | 5 | 16 | **24% FPR** |
| direct | injected | 12 | 9 | 3 | 0 | **100% recall** |
| indirect | injected | 10 | 4 | 6 | 0 | **100% recall** |
| paraphrased | injected | 10 | 0 | 0 | 10 | **0% recall** |
| html-injected | injected | 7 | 7 | 0 | 0 | **100% recall** |
| html-benign | benign | 5 | 0 | 0 | 5 | **0% FPR** |
| obfuscated | injected | 7 | 7 | 0 | 0 | **100% recall** |
| obfuscated-benign | benign | 2 | 0 | 0 | 2 | **0% FPR** |
| addressed-injected | injected | 5 | 0 | 4 | 1 | **80% recall** |
| addressed-benign | benign | 5 | 0 | 1 | 4 | **20% FPR** |

Reading these numbers:

- **The v0.1 categories are unchanged.** The v0.2 additions did not move direct,
  indirect, or paraphrased results. Benign false positives stayed at five.
- **Hidden-text and obfuscation cases are caught.** Seven hidden-element injections
  and seven obfuscated injections were blocked. These are the categories the new
  normalisation and HTML layers were written for. They are dev-set results, so they
  show the mechanisms work, not that they generalise.
- **Addressed-to-AI detection is partial.** One of five phrasings was missed:
  "Message for the language model". I did not add that phrase, because adding it
  after seeing it would be tuning on the dev set. One benign sentence was flagged:
  "When you summarize this report, include the budget section". This is a real
  trade-off in the rule. Words that address the model are also used in ordinary
  instructions to a reader.
- **Paraphrased injections are still not caught.** This remains the most important
  result. The screen only sees vocabulary, and the taint gate is what addresses the
  gap.
- **The gate was checked with a scripted scenario, not a metric.** `make gate-demo`
  shows the correct decisions for a paraphrased injection. A rate would need a
  benchmark of agent tasks and is not part of this version.

Put simply: **the screen now catches hidden and obfuscated attacks it was built
for, still misses reworded ones, and the gate is what limits the damage of a
miss.**

## 8. Limitations

See [LIMITATIONS.md](LIMITATIONS.md) for the full list. The most important:

- The rules are English-only and vocabulary-based. Paraphrase evades the screen,
  and recall on paraphrases is zero in the measured set.
- All labelled data is dev data written by the rule author, so the numbers are a
  regression harness.
- Normalisation is limited to a small look-alike table and a few encodings.
- The gate's protection depends on tool risk tiers and on the approver.
- Thresholds, trust levels, and tool tiers are judgements, not fitted values.

## 9. What would come next

In rough order of value per effort:

1. **Build a held-out set** written by someone who has not seen the rules, and
   report the results separately from dev. This is the number that matters.
2. **Collect a fresh benign set** from real content, and measure the
   false-positive rate there before changing any rule.
3. **Benchmark the gate on agent tasks**, measuring how often a poisoned input
   leads to an unapproved high-risk action.
4. **Evaluate a small classifier** on the held-out set, as an extra signal rather
   than a replacement, and keep it out of the trust boundary.
5. **Reduce the addressed-to-AI false positives** by checking for an imperative
   tied to the model's own behaviour, not just the words "AI" or "assistant".

## 10. Summary

Indirect prompt injection is a real and current problem for any LLM application
that reads content it did not write. A cheap, offline screen now catches hidden
and obfuscated attacks, but it still misses reworded ones and produces false
positives on ordinary text. The more robust idea is the taint gate: once
untrusted content is in the session, dangerous actions need approval, whether or
not the screen noticed anything. The results are measured on a dev set written by
the author. The next step is a held-out set, and the number to watch is paraphrase
recall with the gate in place.
