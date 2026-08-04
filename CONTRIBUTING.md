# Contributing

1. Open an issue describing the proposed change and its trust or interoperability
   impact.
2. Create a focused branch and keep domain behavior separate from adapters.
3. Add tests for every changed invariant or failure mode.
4. Run `ruff check .` and `pytest` before opening a pull request.
5. Document security assumptions and compatibility claims precisely.

Contributions must use synthetic data. Never commit customer, meter, credential,
grid-control, or commercially sensitive information.

