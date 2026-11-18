# injscreen

**v0.1.0** · Python 3.10+ · standard library only · offline · no model calls

`injscreen` is a small, readable screen for **indirect prompt injection**: instructions hidden inside content your LLM application reads but did not write (web pages, documents, emails, tool output, uploads).

It scores text against weighted rules and structural checks, then returns a verdict:

- **allow**: pass through unchanged
- **flag**: wrap in a provenance tag marked as data, not instructions
- **block**: withhold and replace with a placeholder naming the matched signals

It is a first layer, not a defence. The reasoning, assumptions, and measured limits are in [docs/PAPER.md](docs/PAPER.md). Read [docs/LIMITATIONS.md](docs/LIMITATIONS.md) before using it.

## Results at a glance

On the 53-record labelled set in `testdata/` (run `make eval`):

| Category | Result |
|---|---|
| Direct injections (12) | 12 caught (100%) |
| Indirect injections, embedded in ordinary content (10) | 10 caught (100%) |
| Paraphrased injections, avoiding rule vocabulary (10) | **0 caught (0%)** |
| Benign text (21) | 5 flagged (**24% false positives**), 0 blocked |

The paraphrase result is the one to read first. See the paper for why.

## Quick start

```bash
make test                 # 17 unit tests
make eval                 # labelled-set results, per record with --details
make demo                 # screen a sample injection and show the prompt text

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

```python
from injscreen import screen, wrap

result = screen(fetched_page_text, source="https://example.com/page")
prompt_chunk = wrap(fetched_page_text, result)

if result.verdict == "block":
    log.warning("withheld %s: %s", result.source, result.signals)
```

`screen` is pure and fast. Call it on every piece of untrusted text, and log `result.verdict` and `result.signals` rather than the full content.

## Repository layout

```
src/injscreen/
  screen.py      rules, scoring, verdicts, wrapping
  eval.py        labelled-set evaluation
  cli.py         `injscreen check` and `injscreen eval`
testdata/        labelled JSONL records (benign, direct, indirect, paraphrased)
tests/           unit tests and pinned evaluation results
docs/
  PAPER.md       approach, assumptions, considerations, results
  LIMITATIONS.md what this does not do
```

## Design in one paragraph

Rules are regular expressions with weights. Each rule counts once. Two structural checks cover invisible characters and instructions hidden in HTML comments. The score maps to a verdict. No model is called, so the screen cannot itself be injected and runs on every input. The rules are public, which makes them easy to audit and easy to evade; the paper treats that as the central tradeoff.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Any rule change should re-run `make eval` and update the pinned numbers in `tests/test_screen.py` and `docs/PAPER.md` together.

## Security

To report a weakness in the screen, see [SECURITY.md](SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).
