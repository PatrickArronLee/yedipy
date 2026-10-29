# YediPy

YediPy parses X12 without discarding the original source. The lexer exposes source-ordered segments and byte offsets; higher layers validate envelopes and build typed transaction models.

YediPy includes typed models for 32 healthcare transaction sets across X12 `004010`, `005010`, and `005010` pre-errata; see [Transaction Sets](transactions.md). FHIR, HL7, code sets, and MCP tooling are planned but not implemented.

## Design Guarantees

- `X12Interchange.to_source()` returns the original bytes after a successful lexical parse.
- Diagnostics identify structural locations without including source values.
- Unknown segments remain available in the raw segment stream.
- Typed 270 models retain references to raw segments.

Read [Getting Started](getting-started.md) to run the parser, then see [X12 270](x12-270.md) for the supported hierarchy.

For a visual explanation of the core capability, open [EDI becomes a Python object](edi-to-python.html).
