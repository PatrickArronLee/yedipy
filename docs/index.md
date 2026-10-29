---
template: home.html
title: Free, open-source EDI tooling for Python
description: >-
  YediPy is free, open-source EDI parsing and tooling for Python: lossless X12
  lexing, envelope validation and typed Pydantic models for 32 healthcare
  transaction sets.
hide:
  - navigation
  - toc
---

<!--
  Landing page text. The hero (headline, subhead and buttons), layout and
  styles come from overrides/home.html and overrides/assets/stylesheets/home.css.
  The headline is the first line of the manifesto, so the text below starts
  with its second paragraph.
-->

<section class="yp-section yp-manifesto" aria-labelledby="manifesto" markdown>

The manifesto
{ .yp-kicker }

## Why YediPy exists { #manifesto }

<div class="yp-chapters" markdown>

<div class="yp-chapter" markdown>

### The story

Nearly 80 years ago, U.S. military logisticians running the Berlin Airlift developed a data protocol that eventual standard-bearers adopted across multiple global industries: Electronic Data Interchange (EDI).

Today, ANSI X12 EDI quietly runs the backbone of the economy—from supply chains and logistics to banking, insurance, and healthcare.

</div>

<div class="yp-chapter" markdown>

### The problem

Impending CMS mandates will soon require FHIR🔥 interoperability across hospital systems, but adoption won't happen overnight. The biggest hurdle? Accessibility. Standard EDI documentation remains locked behind steep $10,000+ paywalls for what is functionally an "open" protocol. To make matters worse, most existing software toolkits and .NET EDI libraries are tied up in expensive, recurring commercial subscription models that lock developers out of open innovation.

</div>

<div class="yp-chapter" markdown>

### The mission

Years ago, visionaries tried to break this open with [TigerShark](https://pypi.org/project/TigerShark/).

Now, it’s time to finish what was started and spike the ball in the end zone.
{ .yp-punch }

I am making EDI parser specs and tooling—across all industries, versions, and errata—100% free and open-source software: YediPy <span class="yp-emoji" role="img" aria-label="yeti">🫈</span>.
{ .yp-pledge }

</div>

<div class="yp-chapter" markdown>

### Beyond X12

Beyond X12, the roadmap extends directly to support legacy healthcare standard specifications: full coverage for HL7 v2 through version 2.6. While FHIR Release 6 (R6) represents the modern target, legacy integrations aren't disappearing anytime soon, and we need open, reliable bridge tools to backfill the gap.

</div>

<div class="yp-chapter" markdown>

### The invitation

This is a massive effort, and I can't do it alone. If you're passionate about open-source developer tooling, health tech interoperability, or EDI parsing, I'm looking for contributors, testers, and maintainers to help build and refine these spec models.

[Open an issue](https://github.com/PatrickArronLee/yedipy/issues) or [reach out directly](https://github.com/PatrickArronLee) if you want to help tear down these paywalls once and for all.
{ .yp-signoff }

</div>

</div>

</section>

<section class="yp-section yp-section--tint" aria-labelledby="what-works-today" markdown>

Available now
{ .yp-kicker }

## What works today { #what-works-today }

YediPy is pre-release software, but its X12 foundation already works: lossless lexing, envelope validation, typed transaction models and a JSON CLI.
{ .yp-lead }

<div class="yp-features" markdown>

<div class="yp-feature yp-feature--lexer" markdown>

### Lossless X12 lexing

Separators are detected from the fixed-width `ISA` header, and the original bytes, segment order, elements and byte offsets are preserved. Envelope validation checks `ISA`/`IEA`, `GS`/`GE` and `ST`/`SE` nesting, control numbers and counts, then slices each interchange into ordered `ST`/`SE` transactions.

</div>

<div class="yp-feature yp-feature--models" markdown>

### Typed transaction models

Generated Pydantic models for 32 healthcare transaction sets across X12 `004010`, `005010` and `005010` pre-errata: 270, 271, 276, 277, 277A, 278, 820, 820 HIX, 834, 835, 837D, 837I, 837P and 999. Attributes are snake_case, with the OpenFoo names kept as aliases.

</div>

<div class="yp-feature yp-feature--cli" markdown>

### JSON CLI

`yedipy x12 inspect` prints structural JSON. `yedipy x12 validate` returns JSON diagnostics and an exit code your scripts can check. Diagnostics never include source values.

</div>

</div>

<div class="yp-split" markdown>

<div class="yp-panel yp-panel--install" markdown>

### Install

Install today from GitHub (requires Git and Python 3.11 or newer):
{ .yp-install-label .yp-install-label--now }

```shell
python -m pip install git+https://github.com/PatrickArronLee/yedipy
```

First PyPI release coming soon:
{ .yp-install-label .yp-install-label--soon }

```shell
python -m pip install yedipy
```

Then inspect a file:
{ .yp-install-label }

```shell
yedipy x12 inspect claims.edi
```

</div>

<div class="yp-panel" markdown>

### Parse a claim in Python

```python
from pathlib import Path

from yedipy.x12 import parse_x12
from yedipy.x12.transactions import parse_transaction

parsed = parse_x12(Path("claims.edi").read_bytes())
parsed.raise_for_errors()
interchange = parsed.interchange
assert interchange is not None

raw = interchange.transactions[0]
result = parse_transaction(raw, interchange.delimiters)
result.errors       # structural diagnostics
result.transaction  # e.g. TS837P, a typed Pydantic model
```

</div>

</div>

Pre-release also means limits: YediPy is not a payer-ready eligibility workflow, a FHIR mapper, or a complete X12 implementation.
{ .yp-note }

<nav class="yp-readmore" aria-label="Documentation" markdown>

- [Overview](overview.md)
- [Getting started](getting-started.md)
- [Transaction sets](transactions.md)
- [X12 270 support](x12-270.md)
- [API reference](api.md)
- [EDI becomes a Python object](edi-to-python.html)

</nav>

</section>

<section class="yp-section yp-section--night" aria-labelledby="roadmap" markdown>

Where it is headed
{ .yp-kicker }

## Roadmap { #roadmap }

Only the first stage is available today. Everything after it is work still to be done, and a good place to help.
{ .yp-lead }

<ol class="yp-roadmap" markdown>
<li class="yp-step yp-step--available" markdown="block">

### X12 healthcare

Available
{ .yp-status }

Typed models for 32 healthcare transaction sets across X12 `004010`, `005010` and `005010` pre-errata.

</li>
<li class="yp-step yp-step--next" markdown="block">

### All of X12

Next
{ .yp-status }

X12 across all industries, versions and errata, not just healthcare.

</li>
<li class="yp-step yp-step--planned" markdown="block">

### HL7 v2

Planned
{ .yp-status }

Full coverage for HL7 v2 through version 2.6. Not implemented yet.

</li>
<li class="yp-step yp-step--target" markdown="block">

### FHIR R6 bridge

Target
{ .yp-status }

Open bridge tools from legacy EDI to FHIR Release 6 (R6). Not implemented yet.

</li>
</ol>

</section>

<section class="yp-section yp-section--contribute" aria-labelledby="contribute" markdown>

Join in
{ .yp-kicker }

## Help build YediPy { #contribute }

YediPy is looking for contributors, testers and maintainers. Pick the role that fits you.
{ .yp-lead }

<div class="yp-roles" markdown>

<div class="yp-role yp-role--contributors" markdown>

### Contributors

Build and refine spec models, parsers and docs, from today's X12 transaction sets to the HL7 v2 work on the roadmap.

[Browse open issues](https://github.com/PatrickArronLee/yedipy/issues)

</div>

<div class="yp-role yp-role--testers" markdown>

### Testers

Run YediPy against synthetic or de-identified X12 files and report what breaks. Never share real patient data.

[Report a problem](https://github.com/PatrickArronLee/yedipy/issues)

</div>

<div class="yp-role yp-role--maintainers" markdown>

### Maintainers

Review pull requests, triage issues and help steer releases and the roadmap.

[Reach out on GitHub](https://github.com/PatrickArronLee)

</div>

</div>

[Contribute on GitHub](https://github.com/PatrickArronLee/yedipy/issues){ .yp-btn .yp-btn--primary } [Read the docs](overview.md){ .yp-btn .yp-btn--outline }
{ .yp-cta }

</section>
