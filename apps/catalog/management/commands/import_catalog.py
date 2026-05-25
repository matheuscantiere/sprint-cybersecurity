"""Management command: import vehicle catalog from xlsx."""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import (
    Attribute,
    AttributeCategory,
    AttributeValue,
    Brand,
    ValueType,
    VehicleModel,
    Version,
)
from apps.common.utils import slugify_attribute

logger = logging.getLogger("apps.catalog.importer")

# Known label → unit mapping (slugified key → unit string)
UNIT_MAP: dict[str, str] = {
    "potencia": "cv",
    "torque": "Nm",
    "cilindrada": "L",
    "economia_de_combustivel": "km/l",
    "polegadas": "polegadas",
    "peso_em_ordem_de_marchas": "kg",
    "anos_de_garantia": "anos",
}


@dataclass
class RawAttribute:
    label: str
    key: str
    category_slug: str
    category_name: str
    values: dict[str, Any] = field(default_factory=dict)  # version_slug → parsed value
    value_type: str = ""
    unit: str | None = None


@dataclass
class ImportData:
    version_names: list[str] = field(default_factory=list)
    version_slugs: list[str] = field(default_factory=list)
    attributes: list[RawAttribute] = field(default_factory=list)


# ── Public API used by Command and tests ───────────────────────────────────────


def infer_unit(label: str) -> str | None:
    key = slugify_attribute(label)
    if key in UNIT_MAP:
        return UNIT_MAP[key]
    lower = label.lower()
    if "(cada)" in lower or "(unidade)" in lower:
        return "un"
    return None


def parse_workbook(path: str, sheet: str) -> pd.DataFrame:
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, header=None, dtype=object, encoding="utf-8", keep_default_na=True)
    return pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)


def build_intermediate(df: pd.DataFrame) -> ImportData:
    """Walk the DataFrame and build a typed intermediate structure."""
    data = ImportData()

    # Row 0 → version names in columns 1..N (skip NaN cells)
    header_row = df.iloc[0]
    version_cols: list[int] = []
    for col_idx in range(1, len(header_row)):
        cell = header_row.iloc[col_idx]
        if not _is_empty(cell):
            name = str(cell).strip()
            data.version_names.append(name)
            data.version_slugs.append(slugify_attribute(name))
            version_cols.append(col_idx)

    current_category_slug = ""
    current_category_name = ""

    # Rows 2+ (skip row 0=header, row 1=model line)
    for row_idx in range(2, len(df)):
        row = df.iloc[row_idx]
        if _is_empty(row.iloc[0]):
            continue

        label = str(row.iloc[0]).strip()

        # Category separator: all version columns are empty or Coluna1/2/3 placeholders
        if all(_is_category_placeholder(row.iloc[ci]) for ci in version_cols):
            current_category_slug = slugify_attribute(label)
            current_category_name = label
            logger.debug("Category: %s", label)
            continue

        if not current_category_slug:
            logger.warning("Attribute before first category (row %d): %r — skipped", row_idx, label)
            continue

        attr = RawAttribute(
            label=label,
            key=slugify_attribute(label),
            category_slug=current_category_slug,
            category_name=current_category_name,
            unit=infer_unit(label),
        )

        for v_slug, col_idx in zip(data.version_slugs, version_cols, strict=True):
            parsed = _parse_cell(row.iloc[col_idx])
            if parsed is None:
                logger.warning(
                    "NaN at row=%d col=%d (%s / %s) — skipped",
                    row_idx,
                    col_idx,
                    label,
                    v_slug,
                )
                continue
            attr.values[v_slug] = parsed

        if not attr.values:
            logger.warning("All values empty for %r — skipped", label)
            continue

        data.attributes.append(attr)

    return data


def resolve_value_types(data: ImportData) -> ImportData:
    """One pass per attribute: float value → NUMERIC, else BOOLEAN."""
    for attr in data.attributes:
        is_numeric = any(isinstance(v, float) for v in attr.values.values())
        attr.value_type = ValueType.NUMERIC if is_numeric else ValueType.BOOLEAN
    return data


def persist(data: ImportData, brand_name: str, model_name: str) -> dict[str, dict[str, int]]:
    """Write everything to the DB using update_or_create (idempotent)."""
    counts: dict[str, dict[str, int]] = {
        "Brand": {"created": 0, "updated": 0},
        "VehicleModel": {"created": 0, "updated": 0},
        "Version": {"created": 0, "updated": 0},
        "AttributeCategory": {"created": 0, "updated": 0},
        "Attribute": {"created": 0, "updated": 0},
        "AttributeValue": {"created": 0, "updated": 0},
    }

    brand, created = Brand.objects.update_or_create(
        slug=slugify_attribute(brand_name),
        defaults={"name": brand_name},
    )
    _inc(counts, "Brand", created)

    vehicle_model, created = VehicleModel.objects.update_or_create(
        brand=brand,
        slug=slugify_attribute(model_name),
        defaults={"name": model_name},
    )
    _inc(counts, "VehicleModel", created)

    versions: dict[str, Version] = {}
    for v_slug, v_name in zip(data.version_slugs, data.version_names, strict=True):
        version, created = Version.objects.update_or_create(
            model=vehicle_model,
            slug=v_slug,
            defaults={"name": v_name},
        )
        versions[v_slug] = version
        _inc(counts, "Version", created)

    categories: dict[str, AttributeCategory] = {}
    for attr in data.attributes:
        if attr.category_slug in categories:
            continue
        cat, created = AttributeCategory.objects.update_or_create(
            slug=attr.category_slug,
            defaults={"name": attr.category_name, "display_order": len(categories)},
        )
        categories[attr.category_slug] = cat
        _inc(counts, "AttributeCategory", created)

    for attr in data.attributes:
        db_attr, created = Attribute.objects.update_or_create(
            key=attr.key,
            defaults={
                "category": categories[attr.category_slug],
                "label": attr.label,
                "value_type": attr.value_type,
                "unit": attr.unit,
            },
        )
        _inc(counts, "Attribute", created)

        for v_slug, raw_value in attr.values.items():
            if v_slug not in versions:
                continue
            fields = _value_to_db_fields(raw_value, attr.value_type)
            _, created = AttributeValue.objects.update_or_create(
                version=versions[v_slug],
                attribute=db_attr,
                defaults=fields,
            )
            _inc(counts, "AttributeValue", created)

    return counts


# ── Internal helpers ───────────────────────────────────────────────────────────


def _is_empty(cell: Any) -> bool:
    if cell is None:
        return True
    try:
        return bool(pd.isna(cell))
    except (TypeError, ValueError):
        return False


def _is_category_placeholder(cell: Any) -> bool:
    """True for NaN or the 'Coluna1/2/3' placeholders used in category separator rows."""
    if _is_empty(cell):
        return True
    return bool(re.match(r"^Coluna\d+$", str(cell).strip(), re.IGNORECASE))


def _parse_cell(cell: Any) -> Any:
    """Return None (skip), "X" (bool true), "0" (bool false), or float (numeric)."""
    if _is_empty(cell):
        return None
    if isinstance(cell, (int, float)):
        if cell == 0:
            return "0"
        return float(cell)
    s = str(cell).strip()
    if not s:
        return None
    if s.upper() == "X":
        return "X"
    if s == "0":
        return "0"
    try:
        val = float(s)
        return "0" if val == 0 else val
    except ValueError:
        return s


def _value_to_db_fields(parsed_value: Any, value_type: str) -> dict:
    if value_type == ValueType.BOOLEAN:
        present = str(parsed_value).upper() == "X"
        return {
            "boolean_value": present,
            "is_available": present,
            "numeric_value": None,
            "text_value": None,
        }
    if value_type == ValueType.NUMERIC:
        return {
            "numeric_value": float(parsed_value),
            "is_available": True,
            "boolean_value": None,
            "text_value": None,
        }
    return {
        "text_value": str(parsed_value),
        "is_available": True,
        "boolean_value": None,
        "numeric_value": None,
    }


def _inc(counts: dict, entity: str, created: bool) -> None:
    counts[entity]["created" if created else "updated"] += 1


# ── Command ────────────────────────────────────────────────────────────────────


class Command(BaseCommand):
    help = "Import vehicle catalog from an xlsx file."

    def add_arguments(self, parser) -> None:
        parser.add_argument("path", help="Path to the xlsx file")
        parser.add_argument("--brand", default="Ford", help="Brand display name (default: Ford)")
        parser.add_argument(
            "--model", default="Ranger", help="Model display name (default: Ranger)"
        )
        parser.add_argument("--sheet", default="BASE", help="Sheet name (default: BASE)")

    def handle(self, *args, **options) -> None:
        path = options["path"]
        brand_name = options["brand"]
        model_name = options["model"]
        sheet = options["sheet"]

        if not Path(path).exists():
            raise CommandError(f"File not found: {path}")

        self.stdout.write(f"Reading {path!r} (sheet={sheet!r}) …")
        df = parse_workbook(path, sheet)

        self.stdout.write("Parsing …")
        data = build_intermediate(df)
        data = resolve_value_types(data)
        self.stdout.write(
            f"  {len(data.version_names)} version(s), {len(data.attributes)} attribute(s)"
        )

        self.stdout.write("Persisting …")
        try:
            with transaction.atomic():
                counts = persist(data, brand_name, model_name)
        except Exception as exc:
            raise CommandError(f"Import failed and was rolled back: {exc}") from exc

        self.stdout.write("\n── Import summary ──────────────────────────────")
        for entity, c in counts.items():
            self.stdout.write(
                f"  {entity:<20} created={c['created']:>4}  updated={c['updated']:>4}"
            )
        self.stdout.write("────────────────────────────────────────────────\n")
        self.stdout.write(self.style.SUCCESS("Done."))
