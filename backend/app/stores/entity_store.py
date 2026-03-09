from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from ..entities import EntityAttribute, EntityDefinition, EntityModel, load_entity_model_from_file


class EntityStore:
    def __init__(self, *, database_url: str, model_path: str) -> None:
        self._engine: AsyncEngine = create_async_engine(
            database_url,
            pool_pre_ping=True,
        )
        self._model_path = model_path
        self._model: EntityModel | None = None

    async def close(self) -> None:
        await self._engine.dispose()

    async def initialize(self) -> None:
        model = load_entity_model_from_file(self._resolve_model_path(self._model_path))
        self._model = model

        async with self._engine.begin() as connection:
            for entity in model.entities:
                await connection.execute(text(self._create_table_sql(entity)))
                await connection.execute(
                    text(
                        f"""
                        CREATE INDEX IF NOT EXISTS {self._index_name(entity.table_name, "deleted_at")}
                        ON {self._q(entity.table_name)} (deleted_at)
                        """
                    )
                )
                await connection.execute(
                    text(
                        f"""
                        CREATE INDEX IF NOT EXISTS {self._index_name(entity.table_name, "created_at")}
                        ON {self._q(entity.table_name)} (created_at DESC)
                        """
                    )
                )

    def entity_names(self) -> list[str]:
        model = self._require_model()
        return [entity.name for entity in model.entities]

    def entity_metadata(self) -> list[dict[str, Any]]:
        model = self._require_model()
        return [
            {
                "name": entity.name,
                "table": entity.table_name,
                "attributes": [
                    {
                        "name": attribute.name,
                        "type": attribute.data_type,
                        "nullable": attribute.nullable,
                        "unique": attribute.unique,
                        "maxLength": attribute.max_length,
                    }
                    for attribute in entity.attributes
                ],
                "searchableFields": entity.searchable_fields,
                "foreignKeys": [
                    {
                        "column": foreign_key.column,
                        "references": f"{foreign_key.reference_table}.{foreign_key.reference_column}",
                        "onDelete": foreign_key.on_delete,
                    }
                    for foreign_key in entity.foreign_keys
                ],
            }
            for entity in model.entities
        ]

    async def create_record(self, entity_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        entity = self._entity(entity_name)
        column_values = self._coerce_payload(entity, payload, operation="create")
        record_id = str(uuid.uuid4())

        columns = ["id", *column_values.keys()]
        placeholders = [":id", *[f":{column}" for column in column_values.keys()]]
        sql = text(
            f"""
            INSERT INTO {self._q(entity.table_name)} ({", ".join(self._q(column) for column in columns)})
            VALUES ({", ".join(placeholders)})
            RETURNING *
            """
        )
        params: dict[str, Any] = {"id": record_id, **column_values}

        async with self._engine.begin() as connection:
            result = await connection.execute(sql, params)
            row = result.mappings().first()
            if row is None:
                raise RuntimeError(f"Insert failed for entity '{entity_name}'")
            return self._serialize_row(dict(row))

    async def get_record(self, entity_name: str, record_id: str) -> dict[str, Any] | None:
        entity = self._entity(entity_name)
        normalized_id = self._normalize_uuid(record_id)
        sql = text(
            f"""
            SELECT *
            FROM {self._q(entity.table_name)}
            WHERE id = :id AND deleted_at IS NULL
            """
        )

        async with self._engine.begin() as connection:
            result = await connection.execute(sql, {"id": normalized_id})
            row = result.mappings().first()
            if row is None:
                return None
            return self._serialize_row(dict(row))

    async def list_records(
        self,
        entity_name: str,
        *,
        limit: int,
        offset: int,
        search_query: str | None = None,
    ) -> dict[str, Any]:
        entity = self._entity(entity_name)

        where_clauses = ["deleted_at IS NULL"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if search_query:
            search = search_query.strip()
            if search:
                or_clauses = [
                    f"CAST({self._q(field)} AS TEXT) ILIKE :search_query"
                    for field in entity.searchable_fields
                ]
                if or_clauses:
                    params["search_query"] = f"%{search}%"
                    where_clauses.append(f"({' OR '.join(or_clauses)})")

        where_sql = " AND ".join(where_clauses)
        list_sql = text(
            f"""
            SELECT *
            FROM {self._q(entity.table_name)}
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
            """
        )
        count_sql = text(
            f"""
            SELECT COUNT(*) AS count
            FROM {self._q(entity.table_name)}
            WHERE {where_sql}
            """
        )

        async with self._engine.begin() as connection:
            rows_result = await connection.execute(list_sql, params)
            rows = [self._serialize_row(dict(row)) for row in rows_result.mappings().all()]

            count_result = await connection.execute(count_sql, params)
            count_row = count_result.mappings().first()
            total = int(count_row["count"]) if count_row is not None else 0

        return {
            "items": rows,
            "limit": limit,
            "offset": offset,
            "total": total,
        }

    async def update_record(
        self,
        entity_name: str,
        *,
        record_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        entity = self._entity(entity_name)
        normalized_id = self._normalize_uuid(record_id)
        column_values = self._coerce_payload(entity, payload, operation="update")
        if not column_values:
            raise ValueError("At least one attribute must be provided for update")

        set_clause = ", ".join([f"{self._q(column)} = :{column}" for column in column_values.keys()])
        sql = text(
            f"""
            UPDATE {self._q(entity.table_name)}
            SET {set_clause}, updated_at = NOW()
            WHERE id = :id AND deleted_at IS NULL
            RETURNING *
            """
        )
        params: dict[str, Any] = {"id": normalized_id, **column_values}

        async with self._engine.begin() as connection:
            result = await connection.execute(sql, params)
            row = result.mappings().first()
            if row is None:
                return None
            return self._serialize_row(dict(row))

    async def soft_delete_record(self, entity_name: str, *, record_id: str) -> bool:
        entity = self._entity(entity_name)
        normalized_id = self._normalize_uuid(record_id)
        sql = text(
            f"""
            UPDATE {self._q(entity.table_name)}
            SET deleted_at = NOW(), updated_at = NOW()
            WHERE id = :id AND deleted_at IS NULL
            RETURNING id
            """
        )

        async with self._engine.begin() as connection:
            result = await connection.execute(sql, {"id": normalized_id})
            row = result.mappings().first()
            return row is not None

    def _entity(self, entity_name: str) -> EntityDefinition:
        name = entity_name.strip().lower()
        if not name:
            raise KeyError("Entity name must not be empty")
        model = self._require_model()
        entities = model.entity_map()
        entity = entities.get(name)
        if entity is None:
            raise KeyError(f"Entity '{name}' is not defined")
        return entity

    def _require_model(self) -> EntityModel:
        if self._model is None:
            raise RuntimeError("Entity model has not been initialized")
        return self._model

    def _create_table_sql(self, entity: EntityDefinition) -> str:
        column_sql = [
            "id UUID PRIMARY KEY",
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            "updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            "deleted_at TIMESTAMPTZ NULL",
        ]

        for attribute in entity.attributes:
            definition = f"{self._q(attribute.name)} {self._sql_type(attribute)}"
            if not attribute.nullable:
                definition += " NOT NULL"
            if attribute.unique:
                definition += " UNIQUE"
            if attribute.default is not None:
                definition += f" DEFAULT {self._default_sql(attribute, attribute.default)}"
            column_sql.append(definition)

        for foreign_key in entity.foreign_keys:
            column_sql.append(
                (
                    f"FOREIGN KEY ({self._q(foreign_key.column)}) "
                    f"REFERENCES {self._q(foreign_key.reference_table)} ({self._q(foreign_key.reference_column)}) "
                    f"ON DELETE {foreign_key.on_delete}"
                )
            )

        return (
            f"CREATE TABLE IF NOT EXISTS {self._q(entity.table_name)} (\n"
            f"  {',\n  '.join(column_sql)}\n"
            f")"
        )

    def _coerce_payload(
        self,
        entity: EntityDefinition,
        payload: dict[str, Any],
        *,
        operation: str,
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("Payload must be an object")

        attributes = entity.attribute_map()
        unknown_keys = [key for key in payload.keys() if key not in attributes]
        if unknown_keys:
            raise ValueError(f"Unknown attributes for entity '{entity.name}': {', '.join(sorted(unknown_keys))}")

        coerced: dict[str, Any] = {}
        for attribute_name, attribute in attributes.items():
            if attribute_name not in payload:
                if operation == "create" and not attribute.nullable and attribute.default is None:
                    raise ValueError(
                        f"Missing required attribute '{attribute_name}' for entity '{entity.name}'"
                    )
                continue

            value = payload[attribute_name]
            if value is None:
                if not attribute.nullable:
                    raise ValueError(
                        f"Attribute '{attribute_name}' in entity '{entity.name}' cannot be null"
                    )
                coerced[attribute_name] = None
                continue

            coerced[attribute_name] = self._coerce_attribute_value(entity, attribute, value)

        return coerced

    def _coerce_attribute_value(
        self,
        entity: EntityDefinition,
        attribute: EntityAttribute,
        value: Any,
    ) -> Any:
        data_type = attribute.data_type
        if data_type in {"string", "text"}:
            if not isinstance(value, str):
                raise ValueError(f"Attribute '{attribute.name}' in entity '{entity.name}' must be a string")
            if attribute.max_length is not None and len(value) > attribute.max_length:
                raise ValueError(
                    f"Attribute '{attribute.name}' in entity '{entity.name}' exceeds max_length {attribute.max_length}"
                )
            return value

        if data_type == "integer":
            if isinstance(value, bool):
                raise ValueError(f"Attribute '{attribute.name}' in entity '{entity.name}' must be an integer")
            if not isinstance(value, int):
                raise ValueError(f"Attribute '{attribute.name}' in entity '{entity.name}' must be an integer")
            return value

        if data_type == "number":
            if isinstance(value, bool):
                raise ValueError(f"Attribute '{attribute.name}' in entity '{entity.name}' must be a number")
            if isinstance(value, (int, float, Decimal)):
                return float(value)
            raise ValueError(f"Attribute '{attribute.name}' in entity '{entity.name}' must be a number")

        if data_type == "boolean":
            if not isinstance(value, bool):
                raise ValueError(f"Attribute '{attribute.name}' in entity '{entity.name}' must be a boolean")
            return value

        if data_type == "datetime":
            if isinstance(value, datetime):
                return value
            if not isinstance(value, str):
                raise ValueError(f"Attribute '{attribute.name}' in entity '{entity.name}' must be an ISO datetime string")
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed

        if data_type == "date":
            if isinstance(value, date) and not isinstance(value, datetime):
                return value
            if not isinstance(value, str):
                raise ValueError(f"Attribute '{attribute.name}' in entity '{entity.name}' must be an ISO date string")
            return date.fromisoformat(value)

        if data_type == "json":
            if not isinstance(value, (dict, list)):
                raise ValueError(
                    f"Attribute '{attribute.name}' in entity '{entity.name}' must be a JSON object or array"
                )
            return value

        if data_type == "uuid":
            if not isinstance(value, str):
                raise ValueError(f"Attribute '{attribute.name}' in entity '{entity.name}' must be a UUID string")
            return str(uuid.UUID(value))

        raise ValueError(
            f"Attribute '{attribute.name}' in entity '{entity.name}' uses unsupported type '{data_type}'"
        )

    def _sql_type(self, attribute: EntityAttribute) -> str:
        if attribute.data_type == "string":
            if attribute.max_length is not None:
                return f"VARCHAR({attribute.max_length})"
            return "VARCHAR(255)"
        if attribute.data_type == "text":
            return "TEXT"
        if attribute.data_type == "integer":
            return "BIGINT"
        if attribute.data_type == "number":
            return "DOUBLE PRECISION"
        if attribute.data_type == "boolean":
            return "BOOLEAN"
        if attribute.data_type == "datetime":
            return "TIMESTAMPTZ"
        if attribute.data_type == "date":
            return "DATE"
        if attribute.data_type == "json":
            return "JSONB"
        if attribute.data_type == "uuid":
            return "UUID"
        raise ValueError(f"Unsupported SQL type for attribute {attribute.name}: {attribute.data_type}")

    def _default_sql(self, attribute: EntityAttribute, value: Any) -> str:
        if value is None:
            return "NULL"

        if attribute.data_type in {"string", "text", "datetime", "date", "uuid"}:
            return "'" + str(value).replace("'", "''") + "'"
        if attribute.data_type == "boolean":
            if not isinstance(value, bool):
                raise ValueError(
                    f"Default value for attribute '{attribute.name}' must be boolean"
                )
            return "TRUE" if value else "FALSE"
        if attribute.data_type in {"integer", "number"}:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(
                    f"Default value for attribute '{attribute.name}' must be numeric"
                )
            return str(value)
        if attribute.data_type == "json":
            import json

            serialized = json.dumps(value, separators=(",", ":"), ensure_ascii=True).replace("'", "''")
            return f"'{serialized}'::jsonb"

        raise ValueError(f"Default value is not supported for attribute '{attribute.name}'")

    def _serialize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        serialized: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, date):
                serialized[key] = value.isoformat()
            elif isinstance(value, uuid.UUID):
                serialized[key] = str(value)
            elif isinstance(value, Decimal):
                serialized[key] = float(value)
            else:
                serialized[key] = value
        return serialized

    def _normalize_uuid(self, raw_id: str) -> str:
        try:
            return str(uuid.UUID(raw_id))
        except ValueError as exc:
            raise ValueError("Record id must be a valid UUID") from exc

    def _index_name(self, table_name: str, column_name: str) -> str:
        return f"ix_{table_name}_{column_name}"

    def _q(self, identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    def _resolve_model_path(self, configured_path: str) -> Path:
        configured = Path(configured_path)
        candidates = []

        if configured.is_absolute():
            candidates.append(configured)
        else:
            candidates.append((Path.cwd() / configured).resolve())
            candidates.append((Path(__file__).resolve().parents[2] / configured).resolve())

        for candidate in candidates:
            if candidate.exists():
                return candidate

        checked = ", ".join(str(candidate) for candidate in candidates)
        raise FileNotFoundError(f"Entity model file not found. Checked: {checked}")
