from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from ..deps import get_activity_logger, get_entity_store, require_csrf, require_permissions

router = APIRouter(prefix="/entities", tags=["entities"])


class EntityRecordCreateRequest(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class EntityRecordUpdateRequest(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


@router.get("")
async def list_entities(
    request: Request,
    session: dict = Depends(require_permissions("entities:read")),
) -> dict[str, Any]:
    metadata = get_entity_store(request).entity_metadata()
    await get_activity_logger(request).log_event(
        request=request,
        event_type="entities.metadata.read",
        event_category="entities",
        status_code=status.HTTP_200_OK,
        session=session,
        metadata={"count": len(metadata)},
    )
    return {"items": metadata}


@router.post("/{entity_name}/records")
async def create_entity_record(
    request: Request,
    entity_name: str,
    payload: EntityRecordCreateRequest,
    session: dict = Depends(require_permissions("entities:write")),
) -> dict[str, Any]:
    require_csrf(request, session)
    try:
        created = await get_entity_store(request).create_record(entity_name, payload.data)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await get_activity_logger(request).log_event(
        request=request,
        event_type="entities.record.created",
        event_category="entities",
        status_code=status.HTTP_201_CREATED,
        session=session,
        metadata={"entity": entity_name, "id": created.get("id")},
    )
    return {"item": created}


@router.get("/{entity_name}/records")
async def list_entity_records(
    request: Request,
    entity_name: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None),
    session: dict = Depends(require_permissions("entities:read")),
) -> dict[str, Any]:
    try:
        listing = await get_entity_store(request).list_records(
            entity_name,
            limit=limit,
            offset=offset,
            search_query=q,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    await get_activity_logger(request).log_event(
        request=request,
        event_type="entities.record.listed",
        event_category="entities",
        status_code=status.HTTP_200_OK,
        session=session,
        metadata={
            "entity": entity_name,
            "limit": limit,
            "offset": offset,
            "total": listing.get("total", 0),
            "query": q or "",
        },
    )
    return listing


@router.get("/{entity_name}/records/{record_id}")
async def get_entity_record(
    request: Request,
    entity_name: str,
    record_id: str,
    session: dict = Depends(require_permissions("entities:read")),
) -> dict[str, Any]:
    try:
        item = await get_entity_store(request).get_record(entity_name, record_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    await get_activity_logger(request).log_event(
        request=request,
        event_type="entities.record.read",
        event_category="entities",
        status_code=status.HTTP_200_OK,
        session=session,
        metadata={"entity": entity_name, "id": record_id},
    )
    return {"item": item}


@router.patch("/{entity_name}/records/{record_id}")
async def update_entity_record(
    request: Request,
    entity_name: str,
    record_id: str,
    payload: EntityRecordUpdateRequest,
    session: dict = Depends(require_permissions("entities:write")),
) -> dict[str, Any]:
    require_csrf(request, session)
    try:
        updated = await get_entity_store(request).update_record(
            entity_name,
            record_id=record_id,
            payload=payload.data,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    await get_activity_logger(request).log_event(
        request=request,
        event_type="entities.record.updated",
        event_category="entities",
        status_code=status.HTTP_200_OK,
        session=session,
        metadata={"entity": entity_name, "id": record_id},
    )
    return {"item": updated}


@router.delete("/{entity_name}/records/{record_id}")
async def delete_entity_record(
    request: Request,
    entity_name: str,
    record_id: str,
    session: dict = Depends(require_permissions("entities:delete")),
) -> dict[str, Any]:
    require_csrf(request, session)
    try:
        deleted = await get_entity_store(request).soft_delete_record(entity_name, record_id=record_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    await get_activity_logger(request).log_event(
        request=request,
        event_type="entities.record.soft_deleted",
        event_category="entities",
        status_code=status.HTTP_200_OK,
        session=session,
        metadata={"entity": entity_name, "id": record_id},
    )
    return {"ok": True}
