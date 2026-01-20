from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.api.storage.db import get_conn
from src.api.utils.errors import APIError


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _date_to_str(d: Optional[date]) -> Optional[str]:
    return d.isoformat() if d else None


def _row_to_resident(row: Any) -> Dict[str, Any]:
    tags = json.loads(row["tags_json"]) if row["tags_json"] else []
    move_in_date = row["move_in_date"]
    return {
        "id": int(row["id"]),
        "full_name": row["full_name"],
        "unit": row["unit"],
        "phone": row["phone"],
        "email": row["email"],
        "status": row["status"],
        "notes": row["notes"],
        "move_in_date": date.fromisoformat(move_in_date) if move_in_date else None,
        "tags": tags,
        "created_at": datetime.fromisoformat(row["created_at"]),
        "updated_at": datetime.fromisoformat(row["updated_at"]),
    }


# PUBLIC_INTERFACE
def create_resident(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a resident record and return it."""
    now = _now_iso()
    tags_json = json.dumps(payload.get("tags", []))
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO residents (full_name, unit, phone, email, status, notes, move_in_date, tags_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["full_name"],
                payload.get("unit"),
                payload.get("phone"),
                payload.get("email"),
                payload.get("status", "active"),
                payload.get("notes"),
                _date_to_str(payload.get("move_in_date")),
                tags_json,
                now,
                now,
            ),
        )
        resident_id = int(cur.lastrowid)
    return get_resident(resident_id)


# PUBLIC_INTERFACE
def get_resident(resident_id: int) -> Dict[str, Any]:
    """Get a resident by ID."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM residents WHERE id = ?", (resident_id,)).fetchone()
        if row is None:
            raise APIError(status_code=404, code="not_found", message="Resident not found.")
        return _row_to_resident(row)


# PUBLIC_INTERFACE
def update_resident(resident_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update a resident. Only provided fields will be updated."""
    # Ensure exists first for proper 404 semantics
    _ = get_resident(resident_id)

    fields: List[str] = []
    params: List[Any] = []

    if "full_name" in payload:
        fields.append("full_name = ?")
        params.append(payload["full_name"])
    if "unit" in payload:
        fields.append("unit = ?")
        params.append(payload["unit"])
    if "phone" in payload:
        fields.append("phone = ?")
        params.append(payload["phone"])
    if "email" in payload:
        fields.append("email = ?")
        params.append(payload["email"])
    if "status" in payload:
        fields.append("status = ?")
        params.append(payload["status"])
    if "notes" in payload:
        fields.append("notes = ?")
        params.append(payload["notes"])
    if "move_in_date" in payload:
        fields.append("move_in_date = ?")
        params.append(_date_to_str(payload["move_in_date"]))
    if "tags" in payload:
        fields.append("tags_json = ?")
        params.append(json.dumps(payload["tags"]))

    fields.append("updated_at = ?")
    params.append(_now_iso())

    if len(fields) == 1:  # only updated_at
        return get_resident(resident_id)

    params.append(resident_id)

    with get_conn() as conn:
        conn.execute(f"UPDATE residents SET {', '.join(fields)} WHERE id = ?", tuple(params))

    return get_resident(resident_id)


# PUBLIC_INTERFACE
def delete_resident(resident_id: int) -> None:
    """Delete resident by ID."""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM residents WHERE id = ?", (resident_id,))
        if cur.rowcount == 0:
            raise APIError(status_code=404, code="not_found", message="Resident not found.")


def _build_where_clause(
    q: Optional[str],
    status: Optional[str],
    unit: Optional[str],
    tag: Optional[str],
) -> Tuple[str, List[Any]]:
    clauses: List[str] = []
    params: List[Any] = []

    if q:
        clauses.append("(lower(full_name) LIKE ? OR lower(unit) LIKE ? OR lower(email) LIKE ?)")
        like = f"%{q.lower()}%"
        params.extend([like, like, like])

    if status:
        clauses.append("status = ?")
        params.append(status)

    if unit:
        clauses.append("unit = ?")
        params.append(unit)

    if tag:
        # tags_json is a JSON array of strings; use LIKE as a pragmatic filter.
        clauses.append("tags_json LIKE ?")
        params.append(f'%"{tag}"%')

    if not clauses:
        return "", []
    return "WHERE " + " AND ".join(clauses), params


# PUBLIC_INTERFACE
def list_residents(
    *,
    q: Optional[str],
    status: Optional[str],
    unit: Optional[str],
    tag: Optional[str],
    limit: int,
    offset: int,
    sort: str,
    order: str,
) -> Dict[str, Any]:
    """List residents with optional search/filter, pagination, and sorting."""
    allowed_sort = {"full_name", "unit", "status", "created_at", "updated_at", "id"}
    if sort not in allowed_sort:
        raise APIError(status_code=400, code="invalid_sort", message=f"Invalid sort field: {sort}")
    if order not in {"asc", "desc"}:
        raise APIError(status_code=400, code="invalid_order", message="Order must be 'asc' or 'desc'")

    where_sql, params = _build_where_clause(q, status, unit, tag)

    with get_conn() as conn:
        total_row = conn.execute(f"SELECT COUNT(*) as cnt FROM residents {where_sql}", tuple(params)).fetchone()
        total = int(total_row["cnt"]) if total_row else 0

        rows = conn.execute(
            f"""
            SELECT * FROM residents
            {where_sql}
            ORDER BY {sort} {order}
            LIMIT ? OFFSET ?
            """,
            tuple(params + [limit, offset]),
        ).fetchall()

    return {"total": total, "items": [_row_to_resident(r) for r in rows]}
