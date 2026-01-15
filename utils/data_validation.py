"""
Data validation helpers for lightweight schema enforcement.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence

__all__ = [
    "ValidationError",
    "SchemaValidationError",
    "ensure_fields",
    "validate_choices",
    "validate_schema",
    "coerce_types",
]


class ValidationError(Exception):
    """Raised when validation fails."""


class SchemaValidationError(ValidationError):
    """Raised when schema validation fails."""


def ensure_fields(data: Mapping[str, Any], required_fields: Iterable[str]) -> None:
    """
    Ensure required fields exist in the mapping.

    Args:
        data: Mapping to validate.
        required_fields: Fields that must exist and be non-None.

    Raises:
        ValidationError: If any field is missing or empty.
    """
    missing = [field for field in required_fields if data.get(field) in (None, "")]
    if missing:
        raise ValidationError(f"Missing required fields: {', '.join(missing)}")


def validate_choices(
    data: Mapping[str, Any],
    field: str,
    choices: Sequence[Any],
    *,
    allow_none: bool = True,
) -> None:
    """
    Validate a field against allowed choices.

    Args:
        data: Mapping to inspect.
        field: Field name to check.
        choices: Iterable of allowed values.
        allow_none: Whether None is permitted.

    Raises:
        ValidationError: If value not in choices.
    """
    value = data.get(field)
    if value is None and allow_none:
        return
    if value not in choices:
        raise ValidationError(
            f"Field '{field}' must be one of {choices!r}; received {value!r}"
        )


def validate_schema(
    data: Any,
    schema: Dict[str, Any],
    *,
    path: str = "root",
) -> List[str]:
    """
    Validate a Python structure against a minimal JSON-schema-like dict.

    Supported schema keys: type, properties, required, items, enum, minLength, maxLength,
    minimum, maximum.

    Args:
        data: Data to validate.
        schema: Schema definition dictionary.
        path: Current traversal path for error messages.

    Returns:
        List of human-readable validation errors.
    """
    errors: List[str] = []
    expected_type = schema.get("type")

    if expected_type:
        if expected_type == "object" and not isinstance(data, Mapping):
            errors.append(f"{path}: expected object, got {type(data).__name__}")
            return errors
        if expected_type == "array" and not isinstance(data, Sequence):
            errors.append(f"{path}: expected array, got {type(data).__name__}")
            return errors
        if expected_type == "string" and not isinstance(data, str):
            errors.append(f"{path}: expected string, got {type(data).__name__}")
            return errors
        if expected_type == "number" and not isinstance(data, (int, float)):
            errors.append(f"{path}: expected number, got {type(data).__name__}")
            return errors
        if expected_type == "boolean" and not isinstance(data, bool):
            errors.append(f"{path}: expected boolean, got {type(data).__name__}")
            return errors

    if isinstance(data, Mapping):
        required = schema.get("required", [])
        for key in required:
            if key not in data:
                errors.append(f"{path}.{key}: missing required field")

        properties = schema.get("properties", {})
        for key, subschema in properties.items():
            if key in data:
                errors.extend(
                    validate_schema(
                        data[key],
                        subschema,
                        path=f"{path}.{key}",
                    )
                )

    if isinstance(data, Sequence) and not isinstance(data, (str, bytes)):
        item_schema = schema.get("items")
        if item_schema:
            for idx, item in enumerate(data):
                errors.extend(
                    validate_schema(
                        item,
                        item_schema,
                        path=f"{path}[{idx}]",
                    )
                )

    if isinstance(data, str):
        min_length = schema.get("minLength")
        max_length = schema.get("maxLength")
        if min_length is not None and len(data) < min_length:
            errors.append(f"{path}: length {len(data)} < minimum {min_length}")
        if max_length is not None and len(data) > max_length:
            errors.append(f"{path}: length {len(data)} > maximum {max_length}")

    if isinstance(data, (int, float)):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and data < minimum:
            errors.append(f"{path}: value {data} < minimum {minimum}")
        if maximum is not None and data > maximum:
            errors.append(f"{path}: value {data} > maximum {maximum}")

    enum = schema.get("enum")
    if enum is not None and data not in enum:
        errors.append(f"{path}: value {data!r} not in enum {enum!r}")

    return errors


def coerce_types(
    data: Mapping[str, Any],
    field_types: Mapping[str, Callable[[Any], Any]],
) -> Dict[str, Any]:
    """
    Coerce mapping values to specific types.

    Args:
        data: Original mapping.
        field_types: Mapping of field names to callables that coerce the value.

    Returns:
        New dictionary with coerced values.

    Raises:
        ValidationError: When coercion fails.
    """
    coerced: Dict[str, Any] = dict(data)
    for field, converter in field_types.items():
        if field in data and data[field] is not None:
            try:
                coerced[field] = converter(data[field])
            except Exception as exc:
                raise ValidationError(f"Failed to coerce '{field}': {exc}") from exc
    return coerced

