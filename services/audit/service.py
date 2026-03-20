from typing import Optional
from sqlalchemy.orm import Session

from db.models import User
from . import repository
from .schemas import ActionLogResponse, ActionLogFilter, PaginatedActionLogResult


def build_log_details(
    entity_label: Optional[str] = None,
    entity_name: Optional[str] = None,
    context: Optional[str] = None,
) -> Optional[dict[str, str]]:
    """Construit le JSON stocké en base : uniquement la clé `entity_label` (chaîne lisible)."""
    if entity_label is not None:
        s = entity_label.strip()
        return {"entity_label": s} if s else None
    parts: list[str] = []
    if entity_name:
        parts.append(entity_name.strip())
    if context:
        parts.append(context.strip())
    if not parts:
        return None
    label = " — ".join(parts) if len(parts) > 1 else parts[0]
    return {"entity_label": label}


def _details_to_entity_label(details: Optional[dict]) -> Optional[str]:
    """Lit `entity_label` depuis la colonne JSON ; rétrocompatibilité avec anciens formats."""
    if not details or not isinstance(details, dict):
        return None
    el = details.get("entity_label")
    if el is not None:
        return str(el) if not isinstance(el, str) else el
    entity_name = details.get("entity_name") or details.get("name") or details.get("title")
    if entity_name is not None and not isinstance(entity_name, str):
        entity_name = str(entity_name)
    context = details.get("context")
    if context is not None and not isinstance(context, str):
        context = str(context)
    parts: list[str] = []
    if entity_name:
        parts.append(entity_name.strip())
    if context:
        parts.append(context.strip())
    if parts:
        return " — ".join(parts) if len(parts) > 1 else parts[0]
    if "archived_count" in details:
        n = details.get("archived_count", 0)
        return f"Archivage — {n} événement(s)"
    if "archivedCount" in details:
        n = details.get("archivedCount", 0)
        return f"Archivage — {n} événement(s)"
    if "overwritten_count" in details:
        n = details.get("overwritten_count", 0)
        return f"Mise à jour — {n} alerte(s) écrasée(s)"
    if "is_active" in details:
        return f"Alerte — {'active' if details['is_active'] else 'inactive'}"
    if "email" in details and len(details) == 1:
        return str(details["email"])
    if details.get("field") == "password":
        return "Mot de passe modifié"
    return None


def log_action(
    db: Session,
    user: Optional[User],
    action: str,
    resource_type: str,
    *,
    entity_label: Optional[str] = None,
    entity_name: Optional[str] = None,
    context: Optional[str] = None,
) -> None:
    user_id = user.id if user else None
    details_safe = build_log_details(
        entity_label=entity_label,
        entity_name=entity_name,
        context=context,
    )
    repository.create_action_log(
        db,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        details=details_safe,
    )


def _row_to_action_log_response(row) -> "ActionLogResponse":
    first_name = row.user.first_name if row.user else None
    last_name = row.user.last_name if row.user else None
    entity_label = _details_to_entity_label(row.details) or ""
    return ActionLogResponse(
        id=row.id,
        first_name=first_name,
        last_name=last_name,
        action=row.action,
        resource_type=row.resource_type,
        entity_label=entity_label,
        created_at=row.created_at,
    )


def get_action_logs_paginated(
    db: Session,
    filters: ActionLogFilter,
) -> PaginatedActionLogResult:
    resource_type_str = filters.resource_type.value if filters.resource_type else None
    rows, total = repository.get_action_logs(
        db,
        user_id=filters.user_id,
        resource_type=resource_type_str,
        from_date=filters.from_date,
        to_date=filters.to_date,
        skip=filters.skip,
        limit=filters.limit,
    )
    return PaginatedActionLogResult(
        total=total,
        skip=filters.skip,
        limit=filters.limit,
        data=[_row_to_action_log_response(row) for row in rows],
    )
