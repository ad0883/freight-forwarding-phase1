import logging
from typing import Optional
from urllib.parse import urlparse, urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.core.config import settings
from app.models.email import EmailConnection, EmailMessageCache, EmailSuggestion
from app.models.shipment import Shipment
from app.schemas.email import (
    EmailConnectionStatus,
    EmailDebugConfigResponse,
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
    patch_suggestion,
    process_cached_message,
    reject_suggestion,
)
from app.services.gmail_service import (
    GmailOAuthCallbackError,
    OAUTH_ERROR_CALLBACK_FAILED,
    OAUTH_ERROR_STATE_INVALID,
    build_default_query,
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
    return EmailConnectionStatus(
        connected=bool(connection),
        provider="gmail",
        email_address=connection.email_address if connection else None,
        enabled=settings.GMAIL_ENABLED,
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
        handle_oauth_callback(db, code, state)
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
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> EmailDisconnectResponse:
    return EmailDisconnectResponse(disconnected=disconnect_gmail(db, current_user.id))


@router.post("/scan", response_model=EmailScanResponse)
def scan_email(
    payload: EmailScanRequest,
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
    suggestions_created = 0
    for gmail_message_id in message_ids:
        raw_message = get_message(db, connection, gmail_message_id)
        normalized = normalize_message(raw_message)
        message = (
            db.query(EmailMessageCache)
            .filter(
                EmailMessageCache.connection_id == connection.id,
                EmailMessageCache.gmail_message_id == gmail_message_id,
            )
            .first()
        )
        if not message:
            message = EmailMessageCache(connection_id=connection.id, **normalized)
            db.add(message)
        else:
            for field, value in normalized.items():
                setattr(message, field, value)
        db.commit()
        db.refresh(message)
        cached_count += 1
        suggestions_created += process_cached_message(db, message)
    return EmailScanResponse(
        scanned=len(message_ids),
        cached=cached_count,
        suggestions_created=suggestions_created,
    )


@router.get("/messages", response_model=list[EmailMessageListItem])
def list_email_messages(
    classification: Optional[str] = None,
    processed_status: Optional[str] = None,
    shipment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> list[EmailMessageListItem]:
    query = _message_query(db, current_user.id)
    if classification:
        query = query.filter(EmailMessageCache.classification == classification)
    if processed_status:
        query = query.filter(EmailMessageCache.processed_status == processed_status)
    if shipment_id is not None:
        query = query.filter(EmailMessageCache.matched_shipment_id == shipment_id)
    messages = query.order_by(EmailMessageCache.received_at.desc().nullslast(), EmailMessageCache.id.desc()).all()
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
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> list[EmailSuggestionRead]:
    query = _suggestion_query(db, current_user.id)
    if suggestion_status:
        query = query.filter(EmailSuggestion.status == suggestion_status)
    if shipment_id is not None:
        query = query.filter(EmailSuggestion.shipment_id == shipment_id)
    if suggestion_type:
        query = query.filter(EmailSuggestion.suggestion_type == suggestion_type)
    suggestions = query.order_by(EmailSuggestion.created_at.desc(), EmailSuggestion.id.desc()).all()
    return [_suggestion_read(suggestion) for suggestion in suggestions]


@router.patch("/suggestions/{suggestion_id}", response_model=EmailSuggestionRead)
def update_email_suggestion(
    suggestion_id: int,
    payload: EmailSuggestionUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> EmailSuggestionRead:
    suggestion = _get_suggestion_for_user(db, suggestion_id, current_user.id)
    suggestion = patch_suggestion(db, suggestion, payload.shipment_id, payload.extracted_data_json)
    return _suggestion_read(suggestion)


@router.post("/suggestions/{suggestion_id}/apply", response_model=EmailSuggestionApplyResponse)
def apply_email_suggestion(
    suggestion_id: int,
    payload: EmailSuggestionApplyRequest,
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
    return EmailSuggestionApplyResponse(applied=True, suggestion=_suggestion_read(applied), conflicts=[])


@router.post("/suggestions/{suggestion_id}/reject", response_model=EmailSuggestionRead)
def reject_email_suggestion(
    suggestion_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = EmailUser,
) -> EmailSuggestionRead:
    suggestion = _get_suggestion_for_user(db, suggestion_id, current_user.id)
    return _suggestion_read(reject_suggestion(db, suggestion, current_user.id))


def _message_query(db: Session, user_id: int):
    return (
        db.query(EmailMessageCache)
        .join(EmailMessageCache.connection)
        .options(
            joinedload(EmailMessageCache.matched_shipment),
            joinedload(EmailMessageCache.suggestions).joinedload(EmailSuggestion.shipment),
        )
        .filter(EmailConnection.user_id == user_id, EmailConnection.provider == "gmail")
    )


def _suggestion_query(db: Session, user_id: int):
    return (
        db.query(EmailSuggestion)
        .join(EmailSuggestion.email_message)
        .join(EmailMessageCache.connection)
        .options(
            joinedload(EmailSuggestion.shipment),
            joinedload(EmailSuggestion.email_message).joinedload(EmailMessageCache.matched_shipment),
        )
        .filter(EmailConnection.user_id == user_id, EmailConnection.provider == "gmail")
    )


def _get_message_for_user(db: Session, message_id: int, user_id: int) -> EmailMessageCache:
    message = _message_query(db, user_id).filter(EmailMessageCache.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Email message not found")
    return message


def _get_suggestion_for_user(db: Session, suggestion_id: int, user_id: int) -> EmailSuggestion:
    suggestion = _suggestion_query(db, user_id).filter(EmailSuggestion.id == suggestion_id).first()
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
        body_preview=message.body_preview,
        received_at=message.received_at,
        has_attachments=message.has_attachments,
        classification=message.classification,
        matched_shipment_id=message.matched_shipment_id,
        matched_shipment_code=message.matched_shipment.shipment_code if message.matched_shipment else None,
        processed_status=message.processed_status,
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
        suggestion_type=suggestion.suggestion_type,
        classification=suggestion.email_message.classification,
        confidence=suggestion.confidence,
        extracted_data_json=suggestion.extracted_data_json or {},
        status=suggestion.status,
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
