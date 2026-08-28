"""Offline validation for English Master JSON records."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

SCHEMA_FILENAMES: dict[str, str] = {
    "source": "source.schema.json",
    "concept": "concept.schema.json",
    "vocabulary-sense": "vocabulary-sense.schema.json",
    "lesson": "lesson.schema.json",
    "exercise": "exercise.schema.json",
    "ai-practice-prompt": "ai-practice-prompt.schema.json",
}


@dataclass(frozen=True)
class ValidationIssue:
    """A stable, user-readable schema validation failure."""

    instance_path: str
    message: str


class SchemaValidationError(ValueError):
    """Raised when a JSON record does not conform to its schema."""

    def __init__(self, issues: Iterable[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__("; ".join(f"{issue.instance_path}: {issue.message}" for issue in self.issues))


def repository_root() -> Path:
    """Return the repository root that contains the authoritative schemas."""

    source_root = Path(__file__).resolve().parents[2]
    schema_directory = source_root / "schemas"
    if not schema_directory.is_dir():
        raise FileNotFoundError(f"Schema directory not found: {schema_directory}")
    return source_root


def schema_directory() -> Path:
    """Return the absolute path to the authoritative schema directory."""

    return repository_root() / "schemas"


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from *path* with a clear error for non-object values."""

    with path.open("r", encoding="utf-8") as file:
        value: Any = json.load(file)
    if not isinstance(value, dict):
        raise ValueError(f"JSON document must be an object: {path}")
    return value


def load_schemas() -> dict[str, dict[str, Any]]:
    """Load and metaschema-check every local JSON Schema."""

    schemas: dict[str, dict[str, Any]] = {}
    for path in sorted(schema_directory().glob("*.schema.json")):
        schema = load_json(path)
        Draft202012Validator.check_schema(schema)
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            raise ValueError(f"Schema has no nonempty $id: {path}")
        schemas[schema_id] = schema
    if not schemas:
        raise FileNotFoundError(f"No schemas found in {schema_directory()}")
    return schemas


def schema_registry(schemas: dict[str, dict[str, Any]] | None = None) -> Registry:
    """Build a registry that resolves only schemas loaded from this repository."""

    loaded_schemas = schemas if schemas is not None else load_schemas()
    return Registry().with_resources(
        (schema_id, Resource.from_contents(schema, default_specification=DRAFT202012))
        for schema_id, schema in loaded_schemas.items()
    )


def load_schema(schema_name: str) -> dict[str, Any]:
    """Load one supported core schema by its stable logical name."""

    try:
        filename = SCHEMA_FILENAMES[schema_name]
    except KeyError as error:
        supported = ", ".join(sorted(SCHEMA_FILENAMES))
        raise ValueError(f"Unknown schema {schema_name!r}. Supported schemas: {supported}") from error

    schema = load_json(schema_directory() / filename)
    Draft202012Validator.check_schema(schema)
    return schema


def _json_path(error: ValidationError) -> str:
    path = "$"
    for segment in error.absolute_path:
        if isinstance(segment, int):
            path += f"[{segment}]"
        else:
            path += f".{segment}"
    return path


def validation_issues(instance: dict[str, Any], schema_name: str) -> list[ValidationIssue]:
    """Return deterministically ordered issues for an instance and core schema."""

    schemas = load_schemas()
    schema = load_schema(schema_name)
    validator = Draft202012Validator(
        schema,
        registry=schema_registry(schemas),
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(instance), key=lambda error: (_json_path(error), error.message))
    return [ValidationIssue(instance_path=_json_path(error), message=error.message) for error in errors]


def validate_instance(instance: dict[str, Any], schema_name: str) -> None:
    """Raise SchemaValidationError when an instance fails local schema validation."""

    issues = validation_issues(instance, schema_name)
    if issues:
        raise SchemaValidationError(issues)


def validate_file(path: Path, schema_name: str) -> None:
    """Load and validate one JSON file using a supported core schema."""

    validate_instance(load_json(path), schema_name)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(description="Validate English Master JSON records offline.")
    parser.add_argument("--schema", required=True, choices=sorted(SCHEMA_FILENAMES))
    parser.add_argument("paths", nargs="+", type=Path, help="JSON record files to validate")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the validation CLI and return a process exit status."""

    arguments = build_parser().parse_args(argv)
    failed = False
    for path in arguments.paths:
        try:
            validate_file(path, arguments.schema)
        except (OSError, ValueError, json.JSONDecodeError, SchemaValidationError) as error:
            failed = True
            print(f"{path}: INVALID", file=sys.stderr)
            if isinstance(error, SchemaValidationError):
                for issue in error.issues:
                    print(f"  {issue.instance_path}: {issue.message}", file=sys.stderr)
            else:
                print(f"  {error}", file=sys.stderr)
        else:
            print(f"{path}: VALID")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
