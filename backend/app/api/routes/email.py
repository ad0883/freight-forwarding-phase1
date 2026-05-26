import logging
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.core.config import settings
from app.models.email import EmailConnection, EmailMessageCache, EmailSuggestion
from app.models.shipment import Shipment
from app.models.user import User
from app.schemas.email import (
    EmailBulkRejectRequest,
    EmailCleanupRequest,
    EmailCleanupResponse,
    EmailClearPendingRequest,
    EmailClearPendingResponse,
    EmailConnectionStatus,
    EmailDebugConfigResponse,
    EmailDisconnectRequest,
    EmailDisconnectResponse,
    EmailMessageListItem,
    EmailMessageRead,
    EmailOAuthStartResponse,
    EmailScanRequest,
    EmailScanResponse,
    EmailSuggestionApplyRequest,
    EmailSuggestionApplyResponse,
    EmailSuggestionRead,
    EmailSuggestionUpdate,
)
from app.services.email_suggestion_service import (
    EmailSuggestionConflict,
    apply_suggestion,
    bulk_reject_pending,
    cleanup_for_account,
    clear_pending_suggestions,
    delete_suggestion,
    dismiss_suggestion,
    patch_suggestion,
    process_cached_message,
    reject_suggestion,
)
from app.services.audit_service import record_audit_log
from app.services.event_service import OperationalEventType, record_operational_event
from app.services.gmail_service import (
    GmailOAuthCallbackError,
    OAUTH_ERROR_CALLBACK_FAILED,
    OAUTH_ERROR_STATE_INVALID,
    build_default_query,
    clean_body_preview,
    disconnect_gmail,
    frontend_base_url_from_oauth_state,
    get_active_connection,
    get_authorization_url,
    get_message,
    handle_oauth_callback,
    normalize_message,
    search_messages,
)
from app.services.token_crypto_service import TokenCryptoError, encrypt_token


router = APIRouter(prefix="/email", tags=["email-automation"])
logger = logging.getLogger(__name__)


EmailUser = Depends(require_roles("ADMIN", "STAFF"))
AdminUser = Depends(require_roles("ADMIN"))


@router.get("/debug/config", response_model=EmailDebugConfigResponse)
def email_debug_config(
    current_user: AuthenticatedUser = AdminUser,
) -> EmailDebugConfigResponse:
    return EmailDebugConfigResponse(
        gmail_enabled=settings.GMAIL_ENABLED,
        has_google_client_id=bool(settings.GOOGLE_CLIENT_ID.strip()),
        has_google_client_secret=bool(settings.GOOGLE_CLIENT_SECRET.strip()),
        google_redirect_uri=settings.GOOGLE_REDIRECT_URI,
        frontend_base_url=settings.FRONTEND_BASE_URL,
        gmail_scopes=settings.gmail_scopes,
        has_token_encryption_key=bool(settings.TOKEN_ENCRYPTION_KEY.strip()),
        token_encryption_key_valid=_token_encryption_key_valid(),
    )


@router.get("/status", response_model=EmailConnectionStatus)
def email_status(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> EmailConnectionStatus:
    connection = get_active_connection(db, current_user.id)
    pending = 0
    cached = 0
    if connection:
        pending = (
            _suggestion_query(db, current_user.id, current_account_only=True)
            .filter(EmailSuggestion.status == "pending")
            .count()
        )
        cached = (
            _message_query(db, current_user.id, current_account_only=True)
            .filter(EmailMessageCache.visibility == "visible")
            .count()
        )
    return EmailConnectionStatus(
        connected=bool(connection),
        provider="gmail",
        email_address=connection.email_address if connection else None,
        gmail_account_email=(
            connection.gmail_account_email or connection.email_address
            if connection
            else None
        ),
        enabled=settings.GMAIL_ENABLED,
        pending_suggestions=pending,
        cached_messages=cached,
    )


@router.get("/oauth/start", response_model=EmailOAuthStartResponse)
def email_oauth_start(
    request: Request,
    current_user: AuthenticatedUser = EmailUser,
) -> EmailOAuthStartResponse:
    return EmailOAuthStartResponse(
        auth_url=get_authorization_url(
            current_user.id,
            frontend_base_url=_frontend_base_url_from_request(request),
        )
    )


@router.get("/oauth/callback")
def email_oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    redirect_frontend_base_url = frontend_base_url_from_oauth_state(state)
    try:
        logger.info(
            "Gmail OAuth callback start",
            extra={
                "gmail_oauth_has_code": bool(code),
                "gmail_oauth_has_state": bool(state),
                "gmail_oauth_has_provider_error": bool(error),
            },
        )
        if error:
            raise GmailOAuthCallbackError(
                OAUTH_ERROR_CALLBACK_FAILED,
                "provider_redirect",
                "Google OAuth redirected with an error.",
            )
        if not state:
            raise GmailOAuthCallbackError(
                OAUTH_ERROR_STATE_INVALID,
                "callback_validation",
                "Gmail OAuth callback state is missing.",
            )
        if not code:
            raise GmailOAuthCallbackError(
                OAUTH_ERROR_CALLBACK_FAILED,
                "callback_validation",
                "Gmail OAuth callback code is missing.",
            )
        connection = handle_oauth_callback(db, code, state)
        audit_user = _authenticated_user_from_id(db, connection.user_id)
        record_audit_log(
            db,
            audit_user,
            "email.gmail_connected",
            "email_connection",
            entity_id=connection.id,
            entity_label=connection.email_address,
            description="Gmail account connected.",
            metadata={
                "provider": connection.provider,
                "has_email_address": bool(connection.email_address),
                "gmail_account_email_present": bool(connection.gmail_account_email),
            },
            request=request,
        )
    except GmailOAuthCallbackError as exc:
        logger.exception(
            (
                "Gmail OAuth callback failed error_code=%s stage=%s cause_type=%s "
                "oauth_exception_class=%s provider_error_code=%s error_description=%s http_status=%s"
            ),
            exc.error_code,
            exc.stage,
            exc.cause_type,
            exc.diagnostics.get("gmail_oauth_exception_class"),
            exc.diagnostics.get("gmail_oauth_provider_error_code"),
            exc.diagnostics.get("gmail_oauth_error_description"),
            exc.diagnostics.get("gmail_oauth_http_status"),
            extra={
                "gmail_oauth_error_code": exc.error_code,
                "gmail_oauth_stage": exc.stage,
                "gmail_oauth_cause_type": exc.cause_type,
            },
        )
        return _redirect({"email_error": exc.error_code}, redirect_frontend_base_url)
    except Exception as exc:
        logger.exception(
            "Gmail OAuth callback failed",
            extra={
                "gmail_oauth_error_code": OAUTH_ERROR_CALLBACK_FAILED,
                "gmail_oauth_stage": "callback",
                "gmail_oauth_cause_type": type(exc).__name__,
            },
        )
        return _redirect({"email_error": OAUTH_ERROR_CALLBACK_FAILED}, redirect_frontend_base_url)
    return _redirect({"connected": "true"}, redirect_frontend_base_url)


@router.post("/disconnect", response_model=EmailDisconnectResponse)
def email_disconnect(
    request: Request,
    payload: EmailDisconnectRequest = EmailDisconnectRequest(),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> EmailDisconnectResponse:
    connection = get_active_connection(db, current_user.id)
    cleanup_email = connection.gmail_account_email or connection.email_address if connection else None
    cleanup_summary = {"suggestions_rejected": 0, "messages_hidden": 0}
    if connection and payload.clear_cache:
        cleanup_summary = cleanup_for_account(
            db,
            user_id=current_user.id,
            gmail_account_email=cleanup_email,
            reviewer_user_id=current_user.id,
        )
        connection.last_cleanup_at = datetime.utcnow()
        db.commit()
    disconnected = disconnect_gmail(db, current_user.id)
    if disconnected:
        record_audit_log(
            db,
            current_user,
            "email.gmail_disconnected",
            "email_connection",
            entity_id=connection.id if connection else None,
            entity_label=connection.email_address if connection else None,
            description="Gmail account disconnected.",
            metadata={
                "provider": "gmail",
                "clear_cache": payload.clear_cache,
                **cleanup_summary,
            },
            request=request,
        )
    return EmailDisconnectResponse(
        disconnected=disconnected,
        suggestions_rejected=cleanup_summary["suggestions_rejected"],
        messages_hidden=cleanup_summary["messages_hidden"],
    )


@router.post("/cleanup", response_model=EmailCleanupResponse)
def email_cleanup(
    request: Request,
    payload: EmailCleanupRequest = EmailCleanupRequest(),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> EmailCleanupResponse:
    connection = get_active_connection(db, current_user.id)
    target_email = payload.gmail_account_email
    if not target_email and connection:
        target_email = connection.gmail_account_email or connection.email_address
    summary = cleanup_for_account(
        db,
        user_id=current_user.id,
        gmail_account_email=target_email,
        reviewer_user_id=current_user.id,
        hide_messages=payload.hide_messages,
        reject_pending=payload.reject_pending,
    )
    record_audit_log(
        db,
        current_user,
        "email.cleanup",
        "email_connection",
        entity_id=connection.id if connection else None,
        entity_label=target_email,
        description="Gmail cache cleanup executed.",
        metadata={
            "scope_email_present": bool(target_email),
            "hide_messages": payload.hide_messages,
            "reject_pending": payload.reject_pending,
            **summary,
        },
        request=request,
    )
    return EmailCleanupResponse(**summary)


@router.post("/scan", response_model=EmailScanResponse)
def scan_email(
    payload: EmailScanRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> EmailScanResponse:
    connection = get_active_connection(db, current_user.id)
    if not connection:
        raise HTTPException(status_code=400, detail="Gmail is not connected.")
    query = payload.query or build_default_query(payload.lookback_days or settings.EMAIL_LOOKBACK_DAYS)
    max_results = min(payload.max_results or settings.EMAIL_MAX_RESULTS, settings.EMAIL_MAX_RESULTS)
    message_ids = search_messages(db, connection, query, max_results)
    cached_count = 0
    duplicates_skipped = 0
    suggestions_created = 0
    account_email = connection.gmail_account_email or connection.email_address
    for gmail_message_id in message_ids:
        raw_message = get_message(db, connection, gmail_message_id)
        normalized = normalize_message(raw_message)
        existing = (
            db.query(EmailMessageCache)
            .filter(
                EmailMessageCache.connection_id == connection.id,
                EmailMessageCache.gmail_message_id == gmail_message_id,
            )
            .first()
        )
        was_new = existing is None
        if existing:
            duplicates_skipped += 1
            for field, value in normalized.items():
                setattr(existing, field, value)
            existing.user_id = connection.user_id
            existing.gmail_account_email = account_email
            existing.subject_hash = _subject_hash(normalized.get("subject"))
            if existing.visibility == "hidden":
                existing.visibility = "visible"
            message = existing
        else:
            message = EmailMessageCache(
                connection_id=connection.id,
                user_id=connection.user_id,
                gmail_account_email=account_email,
                visibility="visible",
                subject_hash=_subject_hash(normalized.get("subject")),
                **normalized,
            )
            db.add(message)
        db.commit()
        db.refresh(message)
        if was_new:
            cached_count += 1
        suggestions_created += process_cached_message(db, message)
    response = EmailScanResponse(
        scanned=len(message_ids),
        cached=cached_count,
        suggestions_created=suggestions_created,
        duplicates_skipped=duplicates_skipped,
    )
    record_audit_log(
        db,
        current_user,
        "email.scan_completed",
        "email_connection",
        entity_id=connection.id,
        entity_label=connection.email_address,
        description="Gmail scan completed.",
        metadata={
            "query_present": bool(payload.query),
            "lookback_days": payload.lookback_days or settings.EMAIL_LOOKBACK_DAYS,
            "max_results": max_results,
            "scanned": response.scanned,
            "cached": response.cached,
            "duplicates_skipped": response.duplicates_skipped,
            "suggestions_created": response.suggestions_created,
        },
        request=request,
    )
    return response


@router.get("/messages", response_model=list[EmailMessageListItem])
def list_email_messages(
    classification: Optional[str] = None,
    processed_status: Optional[str] = None,
    shipment_id: Optional[int] = None,
    include_hidden: bool = False,
    current_account_only: bool = True,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> list[EmailMessageListItem]:
    query = _message_query(db, current_user.id, current_account_only=current_account_only)
    if classification:
        query = query.filter(EmailMessageCache.classification == classification)
    if processed_status:
        query = query.filter(EmailMessageCache.processed_status == processed_status)
    if shipment_id is not None:
        query = query.filter(EmailMessageCache.matched_shipment_id == shipment_id)
    if not include_hidden:
        query = query.filter(EmailMessageCache.visibility == "visible")
    messages = query.order_by(
        EmailMessageCache.received_at.desc().nullslast(), EmailMessageCache.id.desc()
    ).all()
    return [_message_list_item(message) for message in messages]


@router.get("/messages/{message_id}", response_model=EmailMessageRead)
def get_email_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> EmailMessageRead:
    message = _get_message_for_user(db, message_id, current_user.id)
    return _message_read(message)


@router.get("/suggestions", response_model=list[EmailSuggestionRead])
def list_email_suggestions(
    suggestion_status: str = Query(default="pending", alias="status"),
    shipment_id: Optional[int] = None,
    suggestion_type: Optional[str] = None,
    current_account_only: bool = True,
    include_low_confidence: bool = True,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> list[EmailSuggestionRead]:
    query = _suggestion_query(db, current_user.id, current_account_only=current_account_only)
    if suggestion_status:
        query = query.filter(EmailSuggestion.status == suggestion_status)
    if shipment_id is not None:
        query = query.filter(EmailSuggestion.shipment_id == shipment_id)
    if suggestion_type:
        query = query.filter(EmailSuggestion.suggestion_type == suggestion_type)
    if not include_low_confidence:
        query = query.filter(
            (EmailSuggestion.confidence >= 0.7) | (EmailSuggestion.shipment_id.isnot(None))
        )
    suggestions = query.order_by(
        EmailSuggestion.created_at.desc(), EmailSuggestion.id.desc()
    ).all()
    return [_suggestion_read(suggestion) for suggestion in suggestions]


@router.patch("/suggestions/{suggestion_id}", response_model=EmailSuggestionRead)
def update_email_suggestion(
    suggestion_id: int,
    payload: EmailSuggestionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> EmailSuggestionRead:
    suggestion = _get_suggestion_for_user(db, suggestion_id, current_user.id)
    suggestion = patch_suggestion(db, suggestion, payload.shipment_id, payload.extracted_data_json)
    record_audit_log(
        db,
        current_user,
        "email_suggestion.updated",
        "email_suggestion",
        entity_id=suggestion.id,
        entity_label=suggestion.suggestion_type,
        description="Email suggestion review edits saved.",
        metadata={
            "suggestion_type": suggestion.suggestion_type,
            "shipment_id": suggestion.shipment_id,
            "extracted_data_updated": payload.extracted_data_json is not None,
        },
        request=request,
    )
    return _suggestion_read(suggestion)


@router.post("/suggestions/{suggestion_id}/apply", response_model=EmailSuggestionApplyResponse)
def apply_email_suggestion(
    suggestion_id: int,
    payload: EmailSuggestionApplyRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> EmailSuggestionApplyResponse:
    suggestion = _get_suggestion_for_user(db, suggestion_id, current_user.id)
    try:
        applied = apply_suggestion(db, suggestion, current_user.id, force=payload.force)
    except EmailSuggestionConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Suggestion has conflicts.", "conflicts": exc.conflicts},
        ) from exc
    record_audit_log(
        db,
        current_user,
        "email_suggestion.applied",
        "email_suggestion",
        entity_id=applied.id,
        entity_label=applied.suggestion_type,
        description="Email suggestion applied.",
        metadata={"suggestion_type": applied.suggestion_type, "shipment_id": applied.shipment_id, "force": payload.force},
        request=request,
    )
    record_operational_event(
        db,
        OperationalEventType.EMAIL_SUGGESTION_APPLIED.value,
        "email_suggestion",
        entity_id=applied.id,
        entity_label=applied.suggestion_type,
        shipment_id=applied.shipment_id,
        actor_user=current_user,
        source="gmail",
        new_state={
            "suggestion_type": applied.suggestion_type,
            "shipment_id": applied.shipment_id,
            "status": applied.status,
            "confidence": applied.confidence,
        },
        metadata={"force": payload.force},
        request=request,
    )
    return EmailSuggestionApplyResponse(applied=True, suggestion=_suggestion_read(applied), conflicts=[])


@router.post("/suggestions/{suggestion_id}/reject", response_model=EmailSuggestionRead)
@router.patch("/suggestions/{suggestion_id}/reject", response_model=EmailSuggestionRead)
def reject_email_suggestion(
    suggestion_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> EmailSuggestionRead:
    suggestion = _get_suggestion_for_user(db, suggestion_id, current_user.id)
    rejected = reject_suggestion(db, suggestion, current_user.id)
    record_audit_log(
        db,
        current_user,
        "email_suggestion.rejected",
        "email_suggestion",
        entity_id=rejected.id,
        entity_label=rejected.suggestion_type,
        description="Email suggestion rejected.",
        metadata={"suggestion_type": rejected.suggestion_type, "shipment_id": rejected.shipment_id},
        request=request,
    )
    record_operational_event(
        db,
        OperationalEventType.EMAIL_SUGGESTION_REJECTED.value,
        "email_suggestion",
        entity_id=rejected.id,
        entity_label=rejected.suggestion_type,
        shipment_id=rejected.shipment_id,
        actor_user=current_user,
        source="gmail",
        new_state={
            "suggestion_type": rejected.suggestion_type,
            "shipment_id": rejected.shipment_id,
            "status": rejected.status,
            "confidence": rejected.confidence,
        },
        request=request,
    )
    return _suggestion_read(rejected)


@router.patch("/suggestions/{suggestion_id}/dismiss", response_model=EmailSuggestionRead)
def dismiss_email_suggestion(
    suggestion_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> EmailSuggestionRead:
    suggestion = _get_suggestion_for_user(db, suggestion_id, current_user.id)
    dismissed = dismiss_suggestion(db, suggestion, current_user.id)
    record_audit_log(
        db,
        current_user,
        "email_suggestion.dismissed",
        "email_suggestion",
        entity_id=dismissed.id,
        entity_label=dismissed.suggestion_type,
        description="Email suggestion dismissed.",
        metadata={"suggestion_type": dismissed.suggestion_type, "shipment_id": dismissed.shipment_id},
        request=request,
    )
    return _suggestion_read(dismissed)


@router.delete("/suggestions/{suggestion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_email_suggestion(
    suggestion_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AdminUser,
) -> None:
    suggestion = _get_suggestion_for_user(db, suggestion_id, current_user.id)
    if suggestion.status == "applied":
        raise HTTPException(
            status_code=400,
            detail="Applied suggestions cannot be deleted; the resulting business records remain.",
        )
    metadata = {
        "suggestion_type": suggestion.suggestion_type,
        "shipment_id": suggestion.shipment_id,
        "previous_status": suggestion.status,
    }
    delete_suggestion(db, suggestion)
    record_audit_log(
        db,
        current_user,
        "email_suggestion.deleted",
        "email_suggestion",
        entity_id=suggestion_id,
        entity_label=metadata["suggestion_type"],
        description="Email suggestion hard-deleted.",
        metadata=metadata,
        request=request,
    )


@router.post("/suggestions/bulk-reject", response_model=EmailClearPendingResponse)
def bulk_reject_suggestions(
    payload: EmailBulkRejectRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> EmailClearPendingResponse:
    if not payload.suggestion_ids:
        raise HTTPException(status_code=400, detail="suggestion_ids must not be empty.")
    rejected = bulk_reject_pending(
        db,
        current_user.id,
        suggestion_ids=payload.suggestion_ids,
        reviewer_user_id=current_user.id,
    )
    record_audit_log(
        db,
        current_user,
        "email_suggestion.bulk_rejected",
        "email_suggestion",
        description="Bulk reject pending suggestions.",
        metadata={"requested_count": len(payload.suggestion_ids), "rejected": rejected},
        request=request,
    )
    return EmailClearPendingResponse(rejected=rejected)


@router.post("/suggestions/clear-pending", response_model=EmailClearPendingResponse)
def clear_pending(
    payload: EmailClearPendingRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> EmailClearPendingResponse:
    rejected = clear_pending_suggestions(
        db,
        current_user.id,
        reviewer_user_id=current_user.id,
        gmail_account_email=payload.gmail_account_email,
        current_account_only=payload.current_account_only,
        low_confidence=payload.low_confidence,
        no_shipment=payload.no_shipment,
        older_than=payload.older_than,
        suggestion_type=payload.suggestion_type,
    )
    record_audit_log(
        db,
        current_user,
        "email_suggestion.clear_pending",
        "email_suggestion",
        description="Clear pending suggestions with filters.",
        metadata={
            "current_account_only": payload.current_account_only,
            "low_confidence": payload.low_confidence,
            "no_shipment": payload.no_shipment,
            "older_than_present": payload.older_than is not None,
            "suggestion_type": payload.suggestion_type,
            "rejected": rejected,
        },
        request=request,
    )
    return EmailClearPendingResponse(rejected=rejected)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _message_query(db: Session, user_id: int, *, current_account_only: bool = True):
    query = (
        db.query(EmailMessageCache)
        .join(EmailMessageCache.connection)
        .options(
            joinedload(EmailMessageCache.matched_shipment),
            joinedload(EmailMessageCache.suggestions).joinedload(EmailSuggestion.shipment),
        )
        .filter(EmailConnection.user_id == user_id, EmailConnection.provider == "gmail")
    )
    if current_account_only:
        active_email = _active_account_email(db, user_id)
        if active_email:
            query = query.filter(EmailMessageCache.gmail_account_email == active_email)
    return query


def _suggestion_query(db: Session, user_id: int, *, current_account_only: bool = True):
    query = (
        db.query(EmailSuggestion)
        .join(EmailSuggestion.email_message)
        .join(EmailMessageCache.connection)
        .options(
            joinedload(EmailSuggestion.shipment),
            joinedload(EmailSuggestion.email_message).joinedload(EmailMessageCache.matched_shipment),
        )
        .filter(EmailConnection.user_id == user_id, EmailConnection.provider == "gmail")
    )
    if current_account_only:
        active_email = _active_account_email(db, user_id)
        if active_email:
            query = query.filter(EmailMessageCache.gmail_account_email == active_email)
    return query


def _get_message_for_user(db: Session, message_id: int, user_id: int) -> EmailMessageCache:
    message = (
        _message_query(db, user_id, current_account_only=False)
        .filter(EmailMessageCache.id == message_id)
        .first()
    )
    if not message:
        raise HTTPException(status_code=404, detail="Email message not found")
    return message


def _get_suggestion_for_user(db: Session, suggestion_id: int, user_id: int) -> EmailSuggestion:
    suggestion = (
        _suggestion_query(db, user_id, current_account_only=False)
        .filter(EmailSuggestion.id == suggestion_id)
        .first()
    )
    if not suggestion:
        raise HTTPException(status_code=404, detail="Email suggestion not found")
    return suggestion


def _message_list_item(message: EmailMessageCache) -> EmailMessageListItem:
    return EmailMessageListItem(
        id=message.id,
        subject=message.subject,
        sender=message.sender,
        snippet=message.snippet,
        received_at=message.received_at,
        has_attachments=message.has_attachments,
        classification=message.classification,
        matched_shipment_id=message.matched_shipment_id,
        matched_shipment_code=message.matched_shipment.shipment_code if message.matched_shipment else None,
        processed_status=message.processed_status,
        visibility=message.visibility or "visible",
        gmail_account_email=message.gmail_account_email,
        suggestion_count=len(message.suggestions),
    )


def _message_read(message: EmailMessageCache) -> EmailMessageRead:
    return EmailMessageRead(
        id=message.id,
        connection_id=message.connection_id,
        gmail_message_id=message.gmail_message_id,
        thread_id=message.thread_id,
        subject=message.subject,
        sender=message.sender,
        recipients=message.recipients,
        snippet=message.snippet,
        body_preview=clean_body_preview(message.body_preview or ""),
        received_at=message.received_at,
        has_attachments=message.has_attachments,
        classification=message.classification,
        matched_shipment_id=message.matched_shipment_id,
        matched_shipment_code=message.matched_shipment.shipment_code if message.matched_shipment else None,
        processed_status=message.processed_status,
        visibility=message.visibility or "visible",
        gmail_account_email=message.gmail_account_email,
        created_at=message.created_at,
        updated_at=message.updated_at,
        suggestions=[_suggestion_read(suggestion) for suggestion in message.suggestions],
    )


def _suggestion_read(suggestion: EmailSuggestion) -> EmailSuggestionRead:
    shipment = suggestion.shipment
    if not shipment and suggestion.shipment_id:
        shipment = suggestion.email_message.matched_shipment
    return EmailSuggestionRead(
        id=suggestion.id,
        email_message_id=suggestion.email_message_id,
        shipment_id=suggestion.shipment_id,
        shipment_code=shipment.shipment_code if isinstance(shipment, Shipment) else None,
        shipment_is_archived=bool(shipment.is_archived) if isinstance(shipment, Shipment) else False,
        shipment_archive_reason=shipment.archive_reason if isinstance(shipment, Shipment) else None,
        suggestion_type=suggestion.suggestion_type,
        classification=suggestion.email_message.classification,
        confidence=suggestion.confidence,
        extracted_data_json=suggestion.extracted_data_json or {},
        status=suggestion.status,
        gmail_account_email=suggestion.gmail_account_email
        or suggestion.email_message.gmail_account_email,
        created_at=suggestion.created_at,
    )


def _token_encryption_key_valid() -> bool:
    if not settings.TOKEN_ENCRYPTION_KEY.strip():
        return False
    try:
        encrypt_token("configuration-check")
    except TokenCryptoError:
        return False
    return True


def _authenticated_user_from_id(db: Session, user_id: int) -> Optional[AuthenticatedUser]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    return AuthenticatedUser(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def _frontend_base_url_from_request(request: Request) -> Optional[str]:
    for value in [request.headers.get("origin"), request.headers.get("referer")]:
        frontend_base_url = _origin_from_url(value)
        if frontend_base_url and _is_allowed_frontend_base_url(frontend_base_url):
            return frontend_base_url
    return None


def _origin_from_url(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _is_allowed_frontend_base_url(value: str) -> bool:
    allowed = {settings.FRONTEND_BASE_URL.rstrip("/")}
    allowed.update(origin.rstrip("/") for origin in settings.cors_origins)
    return value.rstrip("/") in allowed


def _redirect(params: dict[str, str], frontend_base_url: Optional[str] = None) -> RedirectResponse:
    query = urlencode(params)
    base_url = frontend_base_url if frontend_base_url and _is_allowed_frontend_base_url(frontend_base_url) else settings.FRONTEND_BASE_URL
    return RedirectResponse(f"{base_url.rstrip('/')}/email?{query}")


def _subject_hash(subject: Optional[str]) -> Optional[str]:
    if not subject:
        return None
    import hashlib

    canonical = " ".join(subject.split()).lower()[:512]
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _active_account_email(db: Session, user_id: int) -> Optional[str]:
    connection = (
        db.query(EmailConnection)
        .filter(
            EmailConnection.user_id == user_id,
            EmailConnection.provider == "gmail",
            EmailConnection.is_active.is_(True),
        )
        .order_by(EmailConnection.updated_at.desc(), EmailConnection.id.desc())
        .first()
    )
    if not connection:
        return None
    return connection.gmail_account_email or connection.email_address
