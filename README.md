# injscreen

**v0.2.0** · Python 3.10+ · standard library only · offline · no model calls

`injscreen` is a small, readable toolkit for **indirect prompt injection**: instructions hidden inside content your LLM application reads but did not write (web pages, documents, emails, tool output, uploads).

It has two layers:

- **Screen.** Scores text against weighted rules, normalised views (look-alikes, encodings), and HTML-hidden text, then returns a verdict:
  - **allow**: pass through unchanged
  - **flag**: wrap in a provenance tag marked as data, not instructions
  - **block**: withhold and replace with a placeholder naming the matched signals
- **Gate.** Tracks how tainted a session is after untrusted content enters it, and asks for approval before high-risk tool calls. It limits the damage when the screen misses an attack.

It is a first layer, not a defence. The reasoning, assumptions, and measured limits are in [docs/PAPER.md](docs/PAPER.md). Read [docs/LIMITATIONS.md](docs/LIMITATIONS.md) before using it.

## Results at a glance

All numbers are on the **dev set**, which was written by the rule author. They are a regression harness, not an independent benchmark (run `make eval`).

| Category | Result |
|---|---|
| Direct injections (12) | 12 caught (100%) |
| Indirect injections, embedded in ordinary content (10) | 10 caught (100%) |
| Paraphrased injections, avoiding rule vocabulary (10) | **0 caught (0%)**, mitigated by the gate |
| Hidden-text injections, HTML (7) | 7 caught (100%) |
| Obfuscated injections, encodings and look-alikes (7) | 7 caught (100%) |
| Addressed-to-AI injections (5) | 4 caught (80%) |
| Benign text (21) | 5 flagged (**24% false positives**), 0 blocked |
| Benign HTML (5) / obfuscation-benign (2) | 0 flagged |
| Addressed-to-AI benign (5) | 1 flagged (20%) |

The paraphrase row is the one to read first. See the paper for why.

## Quick start

```bash
make test                 # 50 unit tests
make eval                 # labelled-set results, per record with --details
make demo                 # screen a sample injection and show the prompt text
make gate-demo            # poisoned page, then a send_email with and without the gate

# screen a file or stdin
PYTHONPATH=src python3 -m injscreen check page.html --wrap
cat email.txt | PYTHONPATH=src python3 -m injscreen check - --wrap
```

Or install the CLI:

```bash
pip install .
injscreen check page.html --wrap
```

## Use in code

Screen a piece of text:

```python
from injscreen import screen, wrap

result = screen(fetched_page_text, source="https://example.com/page", trust="web")
prompt_chunk = wrap(fetched_page_text, result)

if result.verdict == "block":
    log.warning("withheld %s: %s", result.source, result.signals)
```

Gate a session's tool calls:

```python
from injscreen import TaintGate

gate = TaintGate(approver=lambda tool, args: ask_a_human(tool, args))

prompt_chunk = gate.ingest(fetched_page_text, source="web:faq")  # taints the session
decision = gate.authorize("send_email", {"to": to, "body": body})
if decision.action == "allow":
    send_email(to, body)
```

`screen` is pure and fast. Call it on every piece of untrusted text, and log verdicts and signal names rather than the full content.

## Repository layout

```
src/injscreen/
  screen.py      rules, trust levels, verdicts, wrapping
  normalize.py   look-alike folding, encodings, decoded views
  htmlscan.py    visible vs hidden text in HTML
  gate.py        taint tracking and tool-call authorisation
  eval.py        labelled-set evaluation
  cli.py         `injscreen check` and `injscreen eval`
examples/
  gate_demo.py   scripted poisoned-page scenario, no model
testdata/        labelled JSONL records (dev set, seven files)
tests/           unit tests and pinned evaluation results
docs/
  PAPER.md       approach, assumptions, considerations, results
  LIMITATIONS.md what this does not do
```

## Design in one paragraph

Rules are regular expressions with weights, and each rule counts once. The screen runs them on normalised views of the text and on the hidden parts of HTML, then maps the score to a verdict with thresholds set by the trust level of the source. The gate records a session taint that only rises, and makes high-risk tool calls wait for approval once untrusted content has entered. No model is called, so the controls cannot themselves be injected. The rules are public, which makes them easy to audit and easy to evade; the paper treats the gate as the answer to that trade-off.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Any rule change should re-run `make eval` and update the pinned numbers in `tests/test_screen.py` and `docs/PAPER.md` together.

## Security

To report a weakness in the screen or gate, see [SECURITY.md](SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).
