"""Generate typed X12 transaction-set models from OpenFoo OpenAPI specifications.

Usage::

    python tools/generate_x12_models.py PATH/TO/open-api-specs

The specification directory must contain ``004010``, ``005010``, and ``005010-pre-errata``
folders of ``en-<id>-OpenFoo.json`` files. Generated modules are written to
``src/yedipy/x12/transactions/<release package>/``; the specifications themselves are not
copied into the repository.
"""

from __future__ import annotations

import argparse
import json
import keyword
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRANSACTIONS = ROOT / "src" / "yedipy" / "x12" / "transactions"
RELEASES = {
    "004010": "v4010",
    "005010": "v5010",
    "005010-pre-errata": "v5010_pre_errata",
}
REF_PREFIX = "#/components/schemas/"
_BASES = {
    "composite": "X12Composite",
    "segment": "X12Segment",
    "loop": "X12Loop",
    "group": "X12Group",
    "transaction": "X12TransactionSet",
}

# Spec names occasionally join a short word to the previous one ("EligibilityorBenefit").
_JOINED_WORDS = {
    word: (word[: -len(suffix)], suffix)
    for word, suffix in (
        ("lastor", "or"),
        ("groupor", "or"),
        ("unitor", "or"),
        ("basisfor", "for"),
        ("conditionor", "or"),
        ("stateor", "or"),
        ("coordinationof", "of"),
        ("productor", "or"),
        ("zoneor", "or"),
        ("basisof", "of"),
        ("numberof", "of"),
        ("eligibilityor", "or"),
        ("propertyand", "and"),
        ("payto", "to"),
        ("levelof", "of"),
        ("releaseof", "of"),
        ("raceor", "or"),
        ("diemor", "or"),
        ("placeof", "of"),
        ("bundledor", "or"),
        ("provideror", "or"),
        ("assignmentor", "or"),
        ("predeterminationof", "of"),
        ("dateof", "of"),
        ("onsetof", "of"),
        ("checkor", "or"),
        ("prescriptionor", "or"),
        ("unitsof", "of"),
        ("adjustmentfor", "for"),
        ("authorizationor", "or"),
        ("issueor", "or"),
        ("lengthof", "of"),
        ("daysor", "or"),
        ("classof", "of"),
        ("positionin", "in"),
        ("crownor", "or"),
        ("chargeor", "or"),
        ("nationalor", "or"),
        ("illnessor", "or"),
        ("allowanceor", "or"),
        ("fromor", "or"),
        ("monthsof", "of"),
        ("causeof", "of"),
        ("hearingand", "and"),
        ("returnto", "to"),
        ("assumedand", "and"),
        ("certificateof", "of"),
        ("methodor", "or"),
        ("applicationor", "or"),
        ("symptomsor", "or"),
        ("providerof", "of"),
        ("methodof", "of"),
        ("referencein", "in"),
        ("copyof", "of"),
    )
}
_TOKEN = re.compile(
    r"[0-9]+[A-Z]*(?![a-z])|[A-Z]+[0-9]*(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+[0-9]*|[0-9]+"
)
_RESERVED = {
    "raw_segment",
    "model_config",
    "model_fields",
    "copy",
    "dict",
    "json",
    "schema",
    "construct",
    "validate",
    "fields",
    "parse_obj",
    "parse_raw",
    "parse_file",
    "from_orm",
    "update_forward_refs",
    "schema_json",
    "parse",
}


def _tokens(name: str) -> list[str]:
    tokens: list[str] = []
    for part in name.split("_"):
        for token in _TOKEN.findall(part):
            split = _JOINED_WORDS.get(token.lower())
            if split:
                tokens.extend((token[: len(split[0])], split[1]))
            else:
                tokens.append(token)
    return tokens


def snake_case(name: str) -> str:
    result = "_".join(token.lower() for token in _tokens(name)) or "value"
    if result[0].isdigit():
        result = f"x_{result}"
    if keyword.iskeyword(result) or result in _RESERVED:
        result = f"{result}_"
    return result


def pascal_case(name: str) -> str:
    result = ""
    for token in _tokens(name):
        word = token if token.isupper() or token[0].isdigit() else token[0].upper() + token[1:]
        if result and result[-1].isdigit() and word[0].isdigit():
            result += "V"
        result += word
    return result


@dataclass
class Element:
    name: str
    alias: str
    position: int
    data_type: str
    required: bool
    codes_const: str | None = None
    composite: str | None = None
    repeat: bool = False
    max_items: int | None = None
    min_length: int | None = None
    max_length: int | None = None
    implied_decimals: int = 0


@dataclass
class Child:
    name: str
    alias: str
    target: str
    required: bool
    repeat: bool
    max_items: int | None


@dataclass
class Schema:
    source_name: str
    class_name: str
    kind: str  # composite | segment | loop | group | transaction
    x12_id: str | None
    elements: list[Element] = field(default_factory=list)
    children: list[Child] = field(default_factory=list)


class SpecGenerator:
    def __init__(self, release: str, path: Path) -> None:
        self.release = release
        self.path = path
        spec = json.loads(path.read_text(encoding="utf-8"))
        self.schemas: dict[str, dict[str, Any]] = spec["components"]["schemas"]
        self.top_name = next(
            name for name, schema in self.schemas.items() if "x-OpenFoo-message-id" in schema
        )
        top = self.schemas[self.top_name]
        self.transaction_set_id: str = top["x-OpenFoo-message-id"]
        self.implementation_version: str | None = top.get("x-OpenFoo-message-version")
        self.variant = self.top_name.removeprefix("TS")
        self.codes: dict[str, tuple[str, ...]] = {}
        self.class_names: dict[str, str] = {}
        self.models: dict[str, Schema] = {}
        self._used_class_names: set[str] = set()

    @property
    def module_name(self) -> str:
        return f"ts{self.variant.lower()}"

    def kind(self, name: str) -> str:
        schema = self.schemas[name]
        if "x-OpenFoo-message-id" in schema:
            return "transaction"
        if "x-OpenFoo-segment-id" in schema:
            return "segment"
        if "x-OpenFoo-composite-id" in schema:
            return "composite"
        if "x-OpenFoo-group-type" in schema:
            return "group"
        if schema.get("type") == "object" or "properties" in schema:
            return "loop"
        return "codes"

    def class_name(self, name: str) -> str:
        if name in self.class_names:
            return self.class_names[name]
        if name == self.top_name:
            candidate = self.top_name
        else:
            parts = [part for part in name.split("_") if part not in {self.variant, self.top_name}]
            candidate = pascal_case("_".join(parts))
        unique = candidate
        counter = 2
        while unique in self._used_class_names:
            unique = f"{candidate}V{counter}"
            counter += 1
        self._used_class_names.add(unique)
        self.class_names[name] = unique
        return unique

    def codes_const(self, name: str) -> str:
        const = "_CODES_" + re.sub(r"[^0-9A-Za-z]+", "_", name.removeprefix("X12_ID_")).upper()
        if const not in self.codes:
            self.codes[const] = tuple(str(code) for code in self.schemas[name].get("enum", ()))
        return const

    @staticmethod
    def ref_name(ref: str) -> str:
        return ref.removeprefix(REF_PREFIX)

    def visit(self, name: str) -> None:
        if name in self.models:
            return
        kind = self.kind(name)
        schema = self.schemas[name]
        model = Schema(
            source_name=name,
            class_name=self.class_name(name),
            kind=kind,
            x12_id=schema.get("x-OpenFoo-segment-id")
            or schema.get("x-OpenFoo-composite-id")
            or schema.get("x-OpenFoo-loop-id"),
        )
        self.models[name] = model
        required = set(schema.get("required", ()))
        if kind in {"segment", "composite"}:
            model.elements = self.elements(schema, required)
        else:
            model.children = self.children(schema, required)

    def elements(self, schema: dict[str, Any], required: set[str]) -> list[Element]:
        properties: dict[str, Any] = schema.get("properties", {})
        parsed: list[Element] = []
        for alias, prop in properties.items():
            match = re.search(r"_(\d+)$", alias)
            if not match:
                raise ValueError(f"{self.path}: element without position: {alias}")
            element = Element(
                name=snake_case(alias[: match.start()]),
                alias=alias,
                position=int(match.group(1)),
                data_type="AN",
                required=alias in required,
            )
            if prop.get("type") == "array":
                element.repeat = True
                element.max_items = prop.get("maxItems")
                items = prop.get("items", {})
                if "$ref" in items:
                    prop = {**prop, "$ref": items["$ref"]}
            if "$ref" in prop and self.kind(self.ref_name(prop["$ref"])) == "composite":
                target = self.ref_name(prop["$ref"])
                self.visit(target)
                element.composite = self.class_name(target)
            elif "allOf" in prop:
                element.data_type = "ID"
                element.codes_const = self.codes_const(self.ref_name(prop["allOf"][0]["$ref"]))
            else:
                fmt = str(prop.get("format", "X12_AN")).removeprefix("X12_")
                if fmt.startswith("N"):
                    element.data_type = "N"
                    element.implied_decimals = int(fmt[1:] or 0)
                elif fmt in {"AN", "R", "DT", "TM", "ID"}:
                    element.data_type = fmt
                else:
                    raise ValueError(f"{self.path}: unsupported format {fmt} on {alias}")
                if element.data_type in {"AN", "DT", "TM", "ID"}:
                    element.min_length = prop.get("minLength")
                    element.max_length = prop.get("maxLength")
            parsed.append(element)
        counts: dict[str, int] = {}
        for element in parsed:
            counts[element.name] = counts.get(element.name, 0) + 1
        for element in parsed:
            if counts[element.name] > 1:
                element.name = f"{element.name}_{element.position:02d}"
        return parsed

    def children(self, schema: dict[str, Any], required: set[str]) -> list[Child]:
        properties: dict[str, Any] = schema.get("properties", {})
        result: list[Child] = []
        used: set[str] = set()
        for alias, prop in properties.items():
            repeat = prop.get("type") == "array"
            target = self.ref_name(prop["items"]["$ref"] if repeat else prop["$ref"])
            self.visit(target)
            name = snake_case(alias)
            while name in used:
                name = f"{name}_"
            used.add(name)
            result.append(
                Child(
                    name=name,
                    alias=alias,
                    target=target,
                    required=alias in required,
                    repeat=repeat,
                    max_items=prop.get("maxItems"),
                )
            )
        return result

    def ordered(self) -> list[Schema]:
        ordered: list[Schema] = []
        state: dict[str, int] = {}
        by_class = {name: source for source, name in self.class_names.items()}

        def walk(name: str) -> None:
            if state.get(name) == 2:
                return
            if state.get(name) == 1:
                raise ValueError(f"{self.path}: recursive schema {name}")
            state[name] = 1
            model = self.models[name]
            for element in model.elements:
                if element.composite:
                    walk(by_class[element.composite])
            for child in model.children:
                walk(child.target)
            state[name] = 2
            ordered.append(model)

        walk(self.top_name)
        return ordered

    def render(self, spec_label: str) -> str:
        self.visit(self.top_name)
        ordered = self.ordered()
        version = self.implementation_version or self.release
        bases = {_BASES[model.kind] for model in ordered}
        uses_decimal = any(
            element.data_type == "R" or element.implied_decimals
            for model in ordered
            for element in model.elements
            if not element.composite
        )
        runtime_imports = sorted(bases | {"ChildSpec", "ElementSpec"})
        lines = [
            f'"""Generated X12 {self.transaction_set_id} models for {version} ({self.release}).',
            "",
            f"Generated by tools/generate_x12_models.py from the OpenFoo specification {spec_label}.",
            "Do not edit by hand.",
            '"""',
            "",
            "from __future__ import annotations",
            "",
            *(["from decimal import Decimal"] if uses_decimal else []),
            "from typing import ClassVar",
            "",
            "from pydantic import Field",
            "",
            "from .._runtime import (",
            *(f"    {name}," for name in runtime_imports),
            ")",
            "",
        ]
        used_codes = sorted({e.codes_const for m in ordered for e in m.elements if e.codes_const})
        for const in used_codes:
            codes = self.codes[const]
            values = ", ".join(repr(code) for code in codes)
            trailing = "," if len(codes) == 1 else ""
            lines.append(f"{const}: tuple[str, ...] = ({values}{trailing})  # fmt: skip")
        for model in ordered:
            lines.extend(("", ""))
            lines.extend(self.render_model(model))
        lines.extend(("", "", f'__all__ = ["{self.top_name}"]', ""))
        return "\n".join(lines)

    def render_model(self, model: Schema) -> list[str]:
        base = _BASES[model.kind]
        lines = [
            f"class {model.class_name}({base}):",
            f'    """{_describe(model, self.variant)}"""',
            "",
        ]
        if model.kind == "transaction":
            lines.append(f"    x12_transaction_set_id: ClassVar[str] = {self.transaction_set_id!r}")
            lines.append(
                "    x12_implementation_version: ClassVar[str | None] = "
                f"{self.implementation_version!r}"
            )
            lines.append(f"    x12_release: ClassVar[str] = {self.release!r}")
        elif model.kind in {"segment", "composite"}:
            lines.append(f"    x12_id: ClassVar[str] = {model.x12_id!r}")
        else:
            lines.append(f"    x12_id: ClassVar[str | None] = {model.x12_id!r}")
        if model.kind in {"segment", "composite"}:
            lines.append("    x12_elements: ClassVar[tuple[ElementSpec, ...]] = (")
            for element in model.elements:
                args = [repr(element.name), str(element.position)]
                if element.data_type != "AN":
                    args.append(f"data_type={element.data_type!r}")
                if element.codes_const:
                    args.append(f"codes={element.codes_const}")
                if element.composite:
                    args.append(f"composite={element.composite}")
                if element.repeat:
                    args.append("repeat=True")
                if element.implied_decimals:
                    args.append(f"implied_decimals={element.implied_decimals}")
                lines.append(f"        ElementSpec({', '.join(args)}),")
            lines.extend(("    )", ""))
            lines.extend(self.render_element(element) for element in model.elements)
        else:
            lines.append("    x12_children: ClassVar[tuple[ChildSpec, ...]] = (")
            for child in model.children:
                args = [repr(child.name), self.class_name(child.target)]
                if child.repeat:
                    args.append("repeat=True")
                if child.max_items is not None:
                    args.append(f"max_items={child.max_items}")
                lines.append(f"        ChildSpec({', '.join(args)}),")
            lines.extend(("    )", ""))
            lines.extend(self.render_child(child) for child in model.children)
        return lines

    def render_element(self, element: Element) -> str:
        if element.composite:
            scalar = element.composite
        elif element.data_type == "R" or (element.data_type == "N" and element.implied_decimals):
            scalar = "Decimal"
        elif element.data_type == "N":
            scalar = "int"
        else:
            scalar = "str"
        args: list[str] = []
        if element.repeat:
            annotation = f"tuple[{scalar}, ...]"
            if not element.required:
                args.append("default=()")
            args.append(f"alias={element.alias!r}")
            if element.required:
                args.append("min_length=1")
            if element.max_items:
                args.append(f"max_length={element.max_items}")
        else:
            annotation = scalar if element.required else f"{scalar} | None"
            if not element.required:
                args.append("default=None")
            args.append(f"alias={element.alias!r}")
            if scalar == "str":
                if element.min_length:
                    args.append(f"min_length={element.min_length}")
                if element.max_length:
                    args.append(f"max_length={element.max_length}")
        return f"    {element.name}: {annotation} = Field({', '.join(args)})"

    def render_child(self, child: Child) -> str:
        target = self.class_name(child.target)
        args: list[str] = []
        if child.repeat:
            annotation = f"tuple[{target}, ...]"
            if not child.required:
                args.append("default=()")
            args.append(f"alias={child.alias!r}")
            if child.required:
                args.append("min_length=1")
            if child.max_items:
                args.append(f"max_length={child.max_items}")
        else:
            annotation = target if child.required else f"{target} | None"
            if not child.required:
                args.append("default=None")
            args.append(f"alias={child.alias!r}")
        return f"    {child.name}: {annotation} = Field({', '.join(args)})"


def _describe(model: Schema, variant: str) -> str:
    source = model.source_name
    if model.kind in {"loop", "group"} and model.children:
        source = model.children[0].alias
    words = " ".join(
        token if token.isupper() or token[0].isdigit() else token.lower()
        for token in _tokens(source)
        if token != variant
    )
    label = {
        "composite": "Composite",
        "segment": "Segment",
        "loop": "Loop",
        "group": "Unordered group",
        "transaction": "Transaction set",
    }[model.kind]
    suffix = f" {model.x12_id}" if model.x12_id else ""
    return f"{label}{suffix}: {words}."


RegistryRow = tuple[str, str, str, "str | None", str, str]


def generate(spec_root: Path) -> list[RegistryRow]:
    registry: list[RegistryRow] = []
    for release, package in RELEASES.items():
        target_dir = TRANSACTIONS / package
        target_dir.mkdir(parents=True, exist_ok=True)
        rows: list[RegistryRow] = []
        for spec_path in sorted((spec_root / release).glob("*-OpenFoo.json")):
            generator = SpecGenerator(release, spec_path)
            text = generator.render(f"{release}/{spec_path.name}")
            (target_dir / f"{generator.module_name}.py").write_text(text, encoding="utf-8")
            rows.append(
                (
                    release,
                    package,
                    generator.transaction_set_id,
                    generator.implementation_version,
                    generator.module_name,
                    generator.top_name,
                )
            )
            print(f"generated {package}/{generator.module_name}.py")
        registry.extend(rows)
        init = target_dir / "__init__.py"
        if rows and (not init.exists() or "Generated X12" in init.read_text(encoding="utf-8")):
            listing = "\n".join(f"- ``{row[4]}.{row[5]}``" for row in rows)
            example = f"from yedipy.x12.transactions.{package}.{rows[0][4]} import {rows[0][5]}"
            init.write_text(
                f'"""Generated X12 {release} transaction-set models.\n\n'
                f"Import models from their modules, for example::\n\n    {example}\n\n"
                f"Available models:\n\n{listing}\n"
                '"""\n',
                encoding="utf-8",
            )
    _write_registry(registry)
    return registry


def _write_registry(registry: list[RegistryRow]) -> None:
    lines = [
        '"""Generated registry of X12 transaction-set models. Do not edit by hand."""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import NamedTuple",
        "",
        "",
        "class TransactionSetEntry(NamedTuple):",
        '    """Where to import the model for one release and implementation convention."""',
        "",
        "    release: str",
        "    transaction_set_id: str",
        "    implementation_version: str | None",
        "    module: str",
        "    class_name: str",
        "",
        "",
        "TRANSACTION_SETS: tuple[TransactionSetEntry, ...] = (",
    ]
    for release, package, ts_id, version, module, class_name in registry:
        lines.append(
            f"    TransactionSetEntry({release!r}, {ts_id!r}, {version!r}, "
            f'"yedipy.x12.transactions.{package}.{module}", {class_name!r}),'
        )
    lines.extend((")", ""))
    (TRANSACTIONS / "_registry.py").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate X12 models from OpenFoo specs.")
    parser.add_argument("spec_root", type=Path, help="Directory containing OpenFoo release folders")
    parser.add_argument("--no-format", action="store_true", help="Skip ruff formatting")
    args = parser.parse_args(argv)
    registry = generate(args.spec_root)
    if not args.no_format:
        targets = [str(TRANSACTIONS / row[1] / f"{row[4]}.py") for row in registry]
        targets.append(str(TRANSACTIONS / "_registry.py"))
        subprocess.run([sys.executable, "-m", "ruff", "format", "--quiet", *targets], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
