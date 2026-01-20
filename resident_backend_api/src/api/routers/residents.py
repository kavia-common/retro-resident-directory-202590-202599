from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.api.models import ResidentCreate, ResidentListResponse, ResidentOut, ResidentUpdate
from src.api.storage.residents_repo import create_resident, delete_resident, get_resident, list_residents, update_resident
from src.api.utils.auth import require_admin, UserContext

router = APIRouter(prefix="/residents", tags=["Residents"])


@router.get(
    "",
    response_model=ResidentListResponse,
    summary="List residents with search/filter",
    operation_id="list_residents",
)
def list_residents_endpoint(
    q: Optional[str] = Query(None, description="Free-text search across name/unit/email."),
    status: Optional[str] = Query(None, description="Filter by status: active|inactive"),
    unit: Optional[str] = Query(None, description="Filter by exact unit value."),
    tag: Optional[str] = Query(None, description="Filter by tag (string)."),
    limit: int = Query(25, ge=1, le=200, description="Page size."),
    offset: int = Query(0, ge=0, description="Pagination offset."),
    sort: str = Query("full_name", description="Sort field."),
    order: str = Query("asc", description="Sort order: asc|desc"),
) -> ResidentListResponse:
    """List residents (public)."""
    result = list_residents(q=q, status=status, unit=unit, tag=tag, limit=limit, offset=offset, sort=sort, order=order)
    return ResidentListResponse(**result)


@router.get(
    "/{resident_id}",
    response_model=ResidentOut,
    summary="Get resident details",
    operation_id="get_resident",
)
def get_resident_endpoint(resident_id: int) -> ResidentOut:
    """Get a resident by ID (public)."""
    return ResidentOut(**get_resident(resident_id))


@router.post(
    "",
    response_model=ResidentOut,
    summary="Create resident (admin only)",
    operation_id="create_resident",
)
def create_resident_endpoint(payload: ResidentCreate, _: UserContext = Depends(require_admin)) -> ResidentOut:
    """Create a new resident (admin only)."""
    resident = create_resident(payload.model_dump())
    return ResidentOut(**resident)


@router.put(
    "/{resident_id}",
    response_model=ResidentOut,
    summary="Update resident (admin only)",
    operation_id="update_resident",
)
def update_resident_endpoint(
    resident_id: int, payload: ResidentUpdate, _: UserContext = Depends(require_admin)
) -> ResidentOut:
    """Update an existing resident (admin only)."""
    resident = update_resident(resident_id, payload.model_dump(exclude_unset=True))
    return ResidentOut(**resident)


@router.delete(
    "/{resident_id}",
    summary="Delete resident (admin only)",
    operation_id="delete_resident",
)
def delete_resident_endpoint(resident_id: int, _: UserContext = Depends(require_admin)) -> dict:
    """Delete a resident (admin only)."""
    delete_resident(resident_id)
    return {"deleted": True, "id": resident_id}
