# Contributing

Thanks for looking at this. It is a small project with one job: make the screen's behaviour measurable.

## Ground rules

- **Measure before you change a rule.** Run `make eval` before and after. A rule change that improves one category and worsens another should say so in the PR.
- **Add labelled examples with your change.** New phrasings go in the matching `testdata/*.jsonl` file. Do not tune rules on examples you have not added to the set.
- **Keep the paper honest.** If a change moves the pinned numbers in `tests/test_screen.py`, update `docs/PAPER.md` and `README.md` in the same PR.
- **No new dependencies** without a strong reason. The standard-library-only constraint is part of the design.
- **No model calls in the screen.** A screen that calls a model can itself be injected.

## Workflow

```bash
make test
make eval
```

Keep commits focused and describe the measured effect in the message.
