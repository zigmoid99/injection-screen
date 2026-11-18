# Security Policy

## Reporting a weakness

This project's main security-relevant output is the set of ways injected text gets past the screen. If you find a phrasing that evades it, a bypass is useful information, not a vulnerability to hide.

- For a bypass that is only a new phrasing: open a public issue or PR that adds the example to `testdata/paraphrased.jsonl`.
- For anything you would rather not publish first, such as a bypass that would be immediately harmful in a deployed system: open a private security advisory on the repository.

## Scope

This is a screening library. It does not make a model safe, and it should not be the only control between untrusted content and a tool with side effects. Reports about model behaviour in general belong with the model provider.
