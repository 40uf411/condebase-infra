import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
BASE_FIELDS = {"id", "created_at", "updated_at", "deleted_at"}
ALLOWED_ENTITY_TYPES = {"string", "text", "integer", "number", "boolean", "datetime", "date", "json", "uuid"}
ALLOWED_ON_DELETE = {"NO ACTION", "RESTRICT", "CASCADE", "SET NULL", "SET DEFAULT"}


def _clean_name(value: str, *, label: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label} must not be empty")
    if not NAME_PATTERN.match(cleaned):
        raise ValueError(f"{label} contains invalid characters: {cleaned}")
    return cleaned.lower()


def _normalize_type(value: str) -> str:
    cleaned = value.strip().lower()
    if cleaned not in ALLOWED_ENTITY_TYPES:
        raise ValueError(f"Unsupported attribute type '{cleaned}'. Allowed: {sorted(ALLOWED_ENTITY_TYPES)}")
    return cleaned


@dataclass(frozen=True)
class EntityAttribute:
    name: str
    data_type: str
    nullable: bool
    unique: bool
    max_length: int | None
    default: Any


@dataclass(frozen=True)
class EntityForeignKey:
    column: str
    reference_table: str
    reference_column: str
    on_delete: str


@dataclass(frozen=True)
class EntityDefinition:
    name: str
    table_name: str
    attributes: list[EntityAttribute]
    foreign_keys: list[EntityForeignKey]
    searchable_fields: list[str]

    def attribute_map(self) -> dict[str, EntityAttribute]:
        return {attribute.name: attribute for attribute in self.attributes}


@dataclass(frozen=True)
class EntityModel:
    entities: list[EntityDefinition]

    def entity_map(self) -> dict[str, EntityDefinition]:
        return {entity.name: entity for entity in self.entities}


def _load_attribute(raw: dict[str, Any], *, entity_name: str) -> EntityAttribute:
    raw_name = raw.get("name")
    if not isinstance(raw_name, str):
        raise ValueError(f"Attribute in entity '{entity_name}' requires a string 'name'")
    name = _clean_name(raw_name, label=f"Attribute name in entity '{entity_name}'")
    if name in BASE_FIELDS:
        raise ValueError(f"Attribute '{name}' in entity '{entity_name}' conflicts with base entity fields")

    raw_type = raw.get("type")
    if not isinstance(raw_type, str):
        raise ValueError(f"Attribute '{name}' in entity '{entity_name}' requires a string 'type'")
    data_type = _normalize_type(raw_type)

    nullable = bool(raw.get("nullable", True))
    unique = bool(raw.get("unique", False))
    max_length = raw.get("max_length")
    if max_length is not None:
        if not isinstance(max_length, int) or max_length < 1:
            raise ValueError(f"Attribute '{name}' in entity '{entity_name}' has invalid max_length")
        if data_type not in {"string", "text"}:
            raise ValueError(f"Attribute '{name}' max_length is only valid for string/text types")

    return EntityAttribute(
        name=name,
        data_type=data_type,
        nullable=nullable,
        unique=unique,
        max_length=max_length,
        default=raw.get("default"),
    )


def _parse_reference(raw_reference: str, *, entity_name: str) -> tuple[str, str]:
    reference = raw_reference.strip()
    if "." not in reference:
        raise ValueError(
            f"Foreign key reference '{raw_reference}' in entity '{entity_name}' must be in 'table.column' format"
        )
    table_name, column_name = reference.split(".", 1)
    return (
        _clean_name(table_name, label=f"Foreign key table in entity '{entity_name}'"),
        _clean_name(column_name, label=f"Foreign key column in entity '{entity_name}'"),
    )


def _load_foreign_key(raw: dict[str, Any], *, entity_name: str, attribute_names: set[str]) -> EntityForeignKey:
    raw_column = raw.get("column")
    if not isinstance(raw_column, str):
        raise ValueError(f"Foreign key in entity '{entity_name}' requires a string 'column'")
    column = _clean_name(raw_column, label=f"Foreign key column in entity '{entity_name}'")
    if column not in attribute_names:
        raise ValueError(f"Foreign key column '{column}' in entity '{entity_name}' is not declared in attributes")

    raw_reference = raw.get("references")
    if not isinstance(raw_reference, str):
        raise ValueError(f"Foreign key '{column}' in entity '{entity_name}' requires a string 'references'")
    reference_table, reference_column = _parse_reference(raw_reference, entity_name=entity_name)

    on_delete = str(raw.get("on_delete", "NO ACTION")).strip().upper()
    if on_delete not in ALLOWED_ON_DELETE:
        raise ValueError(f"Foreign key '{column}' in entity '{entity_name}' has unsupported on_delete '{on_delete}'")

    return EntityForeignKey(
        column=column,
        reference_table=reference_table,
        reference_column=reference_column,
        on_delete=on_delete,
    )


def _load_entity(raw: dict[str, Any]) -> EntityDefinition:
    raw_name = raw.get("name")
    if not isinstance(raw_name, str):
        raise ValueError("Each entity requires a string 'name'")
    name = _clean_name(raw_name, label="Entity name")

    table_name_value = raw.get("table")
    if isinstance(table_name_value, str) and table_name_value.strip():
        table_name = _clean_name(table_name_value, label=f"Table name for entity '{name}'")
    else:
        table_name = f"{name}s"

    primary_key = raw.get("primary_key", "id")
    if not isinstance(primary_key, str) or _clean_name(primary_key, label=f"Primary key in entity '{name}'") != "id":
        raise ValueError(f"Entity '{name}' must use base primary key 'id'")

    raw_attributes = raw.get("attributes")
    if not isinstance(raw_attributes, list) or not raw_attributes:
        raise ValueError(f"Entity '{name}' must define a non-empty 'attributes' list")

    attributes: list[EntityAttribute] = []
    seen_attributes: set[str] = set()
    for raw_attribute in raw_attributes:
        if not isinstance(raw_attribute, dict):
            raise ValueError(f"Entity '{name}' attributes must be objects")
        attribute = _load_attribute(raw_attribute, entity_name=name)
        if attribute.name in seen_attributes:
            raise ValueError(f"Entity '{name}' contains duplicate attribute '{attribute.name}'")
        seen_attributes.add(attribute.name)
        attributes.append(attribute)

    raw_foreign_keys = raw.get("foreign_keys", [])
    if raw_foreign_keys is None:
        raw_foreign_keys = []
    if not isinstance(raw_foreign_keys, list):
        raise ValueError(f"Entity '{name}' foreign_keys must be a list")

    foreign_keys: list[EntityForeignKey] = []
    for raw_foreign_key in raw_foreign_keys:
        if not isinstance(raw_foreign_key, dict):
            raise ValueError(f"Entity '{name}' foreign_keys entries must be objects")
        foreign_keys.append(
            _load_foreign_key(
                raw_foreign_key,
                entity_name=name,
                attribute_names=seen_attributes,
            )
        )

    raw_searchable = raw.get("searchable_fields")
    searchable_fields: list[str]
    if raw_searchable is None:
        searchable_fields = [
            attribute.name
            for attribute in attributes
            if attribute.data_type in {"string", "text", "uuid"}
        ]
    else:
        if not isinstance(raw_searchable, list):
            raise ValueError(f"Entity '{name}' searchable_fields must be a list")
        normalized = []
        for raw_field in raw_searchable:
            if not isinstance(raw_field, str):
                raise ValueError(f"Entity '{name}' searchable_fields must contain strings")
            field_name = _clean_name(raw_field, label=f"searchable_fields in entity '{name}'")
            if field_name not in seen_attributes:
                raise ValueError(f"Entity '{name}' searchable field '{field_name}' is not defined as an attribute")
            normalized.append(field_name)
        searchable_fields = normalized

    return EntityDefinition(
        name=name,
        table_name=table_name,
        attributes=attributes,
        foreign_keys=foreign_keys,
        searchable_fields=searchable_fields,
    )


def load_entity_model_from_dict(raw_model: dict[str, Any]) -> EntityModel:
    raw_entities = raw_model.get("entities")
    if not isinstance(raw_entities, list):
        raise ValueError("Entity model must contain an 'entities' list")

    entities: list[EntityDefinition] = []
    seen_entity_names: set[str] = set()
    seen_table_names: set[str] = set()
    for raw_entity in raw_entities:
        if not isinstance(raw_entity, dict):
            raise ValueError("All entities must be objects")
        entity = _load_entity(raw_entity)
        if entity.name in seen_entity_names:
            raise ValueError(f"Duplicate entity name '{entity.name}'")
        if entity.table_name in seen_table_names:
            raise ValueError(f"Duplicate table name '{entity.table_name}'")
        seen_entity_names.add(entity.name)
        seen_table_names.add(entity.table_name)
        entities.append(entity)

    return EntityModel(entities=entities)


def load_entity_model_from_file(path: Path) -> EntityModel:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Entity model file must contain a JSON object")
    return load_entity_model_from_dict(payload)


def entity_model_to_dict(model: EntityModel) -> dict[str, Any]:
    return {
        "entities": [
            {
                "name": entity.name,
                "table": entity.table_name,
                "primary_key": "id",
                "attributes": [
                    {
                        "name": attribute.name,
                        "type": attribute.data_type,
                        "nullable": attribute.nullable,
                        "unique": attribute.unique,
                        "max_length": attribute.max_length,
                        "default": attribute.default,
                    }
                    for attribute in entity.attributes
                ],
                "foreign_keys": [
                    {
                        "column": foreign_key.column,
                        "references": f"{foreign_key.reference_table}.{foreign_key.reference_column}",
                        "on_delete": foreign_key.on_delete,
                    }
                    for foreign_key in entity.foreign_keys
                ],
                "searchable_fields": entity.searchable_fields,
            }
            for entity in model.entities
        ]
    }
