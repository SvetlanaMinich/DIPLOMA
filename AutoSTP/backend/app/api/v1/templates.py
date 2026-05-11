from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_async_session
from app.models.template import TemplateType
from app.models.user import User
from app.schemas.template import (
    TemplateCreate,
    TemplateListResponse,
    TemplateOut,
    TemplateUpdate,
    TemplateConfiguration,
)
from app.services import template_service

router = APIRouter()


@router.post("/extract", response_model=TemplateOut)
async def extract_template_endpoint(
    file: UploadFile = File(...),
    name: str | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> Any:
    content = await file.read()
    t = await template_service.extract_and_save_template(
        session=session,
        user=current_user,
        file_content=content,
        filename=file.filename or "document.pdf",
        name=name,
    )
    return _template_to_out(t)


@router.post("/extract-only", response_model=TemplateConfiguration)
async def extract_only_endpoint(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> Any:
    content = await file.read()
    return await template_service.extract_template_from_file(
        file_content=content,
        filename=file.filename or "document.pdf",
    )


@router.post("/", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
async def create_template_endpoint(
    *,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
    template_in: TemplateCreate,
) -> Any:
    t = await template_service.create_template(
        session=session, user=current_user, template_in=template_in
    )
    return _template_to_out(t)


@router.get("/", response_model=TemplateListResponse)
async def list_templates_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    type_filter: TemplateType | None = Query(
        None, description="Фильтр по типу шаблона (system/personal)"
    ),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> Any:
    items, total = await template_service.get_templates(
        session=session,
        user=current_user,
        skip=skip,
        limit=limit,
        type_filter=type_filter,
    )
    return TemplateListResponse(
        items=[_template_to_out(t) for t in items],
        total=total,
    )


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template_endpoint(
    template_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> Any:
    t = await template_service.get_template(
        session=session, template_id=template_id, user=current_user
    )
    return _template_to_out(t)


@router.put("/{template_id}", response_model=TemplateOut)
async def update_template_endpoint(
    template_id: UUID,
    template_in: TemplateUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> Any:
    t = await template_service.update_template(
        session=session,
        template_id=template_id,
        user=current_user,
        template_in=template_in,
    )
    return _template_to_out(t)


@router.delete("/{template_id}", status_code=status.HTTP_200_OK)
async def delete_template_endpoint(
    template_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    await template_service.delete_template(
        session=session, template_id=template_id, user=current_user
    )
    return {"detail": "deleted"}


def _template_to_out(t: template_service.Template) -> TemplateOut:
    return TemplateOut(
        id=t.id,
        user_id=t.user_id,
        name=t.name,
        description=t.description,
        type=t.type,
        template_json=t.template_json,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )
