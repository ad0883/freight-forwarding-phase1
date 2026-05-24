import base64
import logging
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Optional

from fastapi import HTTPException
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token
from app.models.email import EmailConnection
from app.services.token_crypto_service import decrypt_token, encrypt_token, TokenCryptoError


logger = logging.getLogger(__name__)

GMAIL_PROVIDER = "gmail"
GMAIL_TOKEN_URI = "https://oauth2.googleapis.com/token"
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"

OAUTH_ERROR_STATE_INVALID = "state_invalid"
OAUTH_ERROR_TOKEN_EXCHANGE_FAILED = "token_exchange_failed"
OAUTH_ERROR_GMAIL_PROFILE_FAILED = "gmail_profile_failed"
OAUTH_ERROR_TOKEN_ENCRYPTION_FAILED = "token_encryption_failed"
OAUTH_ERROR_DB_SAVE_FAILED = "db_save_failed"
OAUTH_ERROR_CALLBACK_FAILED = "oauth_callback_failed"


class GmailOAuthCallbackError(Exception):
    def __init__(
        self,
        error_code: str,
        stage: str,
        message: str,
        cause_type: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.stage = stage
        self.cause_type = cause_type


def _ensure_gmail_configured() -> None:
    if not settings.GMAIL_ENABLED:
        raise HTTPException(status_code=400, detail="Gmail automation is disabled.")
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=400, detail="Google OAuth client env vars are not configured.")
    if settings.gmail_scopes != [GMAIL_READONLY_SCOPE]:
        raise HTTPException(status_code=400, detail="Phase 5 requires gmail.readonly as the only Gmail scope.")
    try:
        encrypt_token("configuration-check")
    except TokenCryptoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _client_config() -> dict[str, Any]:
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": GMAIL_TOKEN_URI,
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }


def _build_flow(state: Optional[str] = None) -> Flow:
    _ensure_gmail_configured()
    flow = Flow.from_client_config(_client_config(), scopes=settings.gmail_scopes, state=state)
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    return flow


def get_authorization_url(user_id: int) -> str:
    state = create_access_token(
        "gmail-oauth",
        expires_delta=timedelta(minutes=10),
        additional_claims={"uid": user_id, "purpose": "gmail_oauth"},
    )
    flow = _build_flow(state=state)
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return authorization_url


def user_id_from_oauth_state(state: str) -> int:
    try:
        payload = decode_access_token(state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Gmail OAuth state.") from exc
    if payload.get("purpose") != "gmail_oauth" or payload.get("sub") != "gmail-oauth":
        raise HTTPException(status_code=400, detail="Invalid Gmail OAuth state.")
    return int(payload["uid"])


def handle_oauth_callback(db: Session, code: str, state: str) -> EmailConnection:
    try:
        user_id = user_id_from_oauth_state(state)
    except Exception as exc:
        raise GmailOAuthCallbackError(
            OAUTH_ERROR_STATE_INVALID,
            "state_validation",
            "Invalid Gmail OAuth state.",
            type(exc).__name__,
        ) from None

    try:
        flow = _build_flow(state=state)
    except HTTPException as exc:
        error_code = (
            OAUTH_ERROR_TOKEN_ENCRYPTION_FAILED
            if "TOKEN_ENCRYPTION_KEY" in str(exc.detail)
            else OAUTH_ERROR_CALLBACK_FAILED
        )
        raise GmailOAuthCallbackError(
            error_code,
            "flow_configuration",
            "Unable to configure Gmail OAuth callback.",
            type(exc).__name__,
        ) from None
    except Exception as exc:
        raise GmailOAuthCallbackError(
            OAUTH_ERROR_CALLBACK_FAILED,
            "flow_configuration",
            "Unable to configure Gmail OAuth callback.",
            type(exc).__name__,
        ) from None

    logger.info("Gmail OAuth token exchange start", extra={"gmail_oauth_user_id": user_id})
    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        logger.info(
            "Gmail OAuth token exchange end",
            extra={
                "gmail_oauth_user_id": user_id,
                "gmail_oauth_success": False,
                "gmail_oauth_cause_type": type(exc).__name__,
            },
        )
        raise GmailOAuthCallbackError(
            OAUTH_ERROR_TOKEN_EXCHANGE_FAILED,
            "token_exchange",
            "Gmail OAuth token exchange failed.",
            type(exc).__name__,
        ) from None
    credentials = flow.credentials
    logger.info(
        "Gmail OAuth token exchange end",
        extra={
            "gmail_oauth_user_id": user_id,
            "gmail_oauth_success": True,
            "gmail_oauth_has_refresh_token": bool(credentials.refresh_token),
        },
    )

    existing = get_active_connection(db, user_id)
    existing_refresh_token_encrypted = existing.refresh_token_encrypted if existing else None
    if not credentials.refresh_token and not existing_refresh_token_encrypted:
        raise GmailOAuthCallbackError(
            OAUTH_ERROR_TOKEN_EXCHANGE_FAILED,
            "token_exchange",
            "Gmail OAuth did not provide a refresh token.",
        )

    logger.info("Gmail profile fetch start", extra={"gmail_oauth_user_id": user_id})
    try:
        profile = get_profile_from_credentials(credentials)
    except Exception as exc:
        logger.info(
            "Gmail profile fetch end",
            extra={
                "gmail_oauth_user_id": user_id,
                "gmail_oauth_success": False,
                "gmail_oauth_cause_type": type(exc).__name__,
            },
        )
        raise GmailOAuthCallbackError(
            OAUTH_ERROR_GMAIL_PROFILE_FAILED,
            "gmail_profile",
            "Gmail profile fetch failed.",
            type(exc).__name__,
        ) from None
    logger.info(
        "Gmail profile fetch end",
        extra={
            "gmail_oauth_user_id": user_id,
            "gmail_oauth_success": True,
            "gmail_oauth_has_email_address": bool(profile.get("emailAddress")),
        },
    )

    logger.info("Gmail OAuth token encryption start", extra={"gmail_oauth_user_id": user_id})
    try:
        access_token_encrypted = encrypt_token(credentials.token or "")
        refresh_token_encrypted = (
            encrypt_token(credentials.refresh_token)
            if credentials.refresh_token
            else existing_refresh_token_encrypted
        )
    except TokenCryptoError as exc:
        logger.info(
            "Gmail OAuth token encryption end",
            extra={
                "gmail_oauth_user_id": user_id,
                "gmail_oauth_success": False,
                "gmail_oauth_cause_type": type(exc).__name__,
            },
        )
        raise GmailOAuthCallbackError(
            OAUTH_ERROR_TOKEN_ENCRYPTION_FAILED,
            "token_encryption",
            "Gmail token encryption failed.",
            type(exc).__name__,
        ) from None
    except Exception as exc:
        logger.info(
            "Gmail OAuth token encryption end",
            extra={
                "gmail_oauth_user_id": user_id,
                "gmail_oauth_success": False,
                "gmail_oauth_cause_type": type(exc).__name__,
            },
        )
        raise GmailOAuthCallbackError(
            OAUTH_ERROR_TOKEN_ENCRYPTION_FAILED,
            "token_encryption",
            "Gmail token encryption failed.",
            type(exc).__name__,
        ) from None
    logger.info(
        "Gmail OAuth token encryption end",
        extra={"gmail_oauth_user_id": user_id, "gmail_oauth_success": True},
    )

    connection = existing or EmailConnection(user_id=user_id, provider=GMAIL_PROVIDER)
    connection.email_address = profile.get("emailAddress")
    connection.access_token_encrypted = access_token_encrypted
    connection.refresh_token_encrypted = refresh_token_encrypted
    connection.token_expiry = _naive_utc(credentials.expiry)
    connection.scopes = ",".join(settings.gmail_scopes)
    connection.is_active = True

    logger.info("EmailConnection DB save start", extra={"gmail_oauth_user_id": user_id})
    try:
        db.add(connection)
        db.commit()
        db.refresh(connection)
    except Exception as exc:
        db.rollback()
        logger.info(
            "EmailConnection DB save end",
            extra={
                "gmail_oauth_user_id": user_id,
                "gmail_oauth_success": False,
                "gmail_oauth_cause_type": type(exc).__name__,
            },
        )
        raise GmailOAuthCallbackError(
            OAUTH_ERROR_DB_SAVE_FAILED,
            "db_save",
            "EmailConnection save failed.",
            type(exc).__name__,
        ) from None
    logger.info(
        "EmailConnection DB save end",
        extra={"gmail_oauth_user_id": user_id, "gmail_oauth_success": True},
    )
    return connection


def get_active_connection(db: Session, user_id: int) -> Optional[EmailConnection]:
    return (
        db.query(EmailConnection)
        .filter(
            EmailConnection.user_id == user_id,
            EmailConnection.provider == GMAIL_PROVIDER,
            EmailConnection.is_active.is_(True),
        )
        .order_by(EmailConnection.updated_at.desc(), EmailConnection.id.desc())
        .first()
    )


def disconnect_gmail(db: Session, user_id: int) -> bool:
    connection = get_active_connection(db, user_id)
    if not connection:
        return False
    connection.is_active = False
    db.commit()
    return True


def credentials_for_connection(db: Session, connection: EmailConnection) -> Credentials:
    try:
        credentials = Credentials(
            token=decrypt_token(connection.access_token_encrypted),
            refresh_token=decrypt_token(connection.refresh_token_encrypted),
            token_uri=GMAIL_TOKEN_URI,
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=connection.scopes.split(","),
        )
    except TokenCryptoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Unable to refresh Gmail access token.") from exc
        connection.access_token_encrypted = encrypt_token(credentials.token or "")
        if credentials.refresh_token:
            connection.refresh_token_encrypted = encrypt_token(credentials.refresh_token)
        connection.token_expiry = _naive_utc(credentials.expiry)
        db.commit()
        db.refresh(connection)
    return credentials


def get_gmail_service(db: Session, connection: EmailConnection):
    credentials = credentials_for_connection(db, connection)
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def get_profile_from_credentials(credentials: Credentials) -> dict[str, Any]:
    service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
    return service.users().getProfile(userId="me").execute()


def search_messages(db: Session, connection: EmailConnection, query: str, max_results: int) -> list[str]:
    service = get_gmail_service(db, connection)
    try:
        response = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    except HttpError as exc:
        raise HTTPException(status_code=400, detail="Unable to search Gmail messages.") from exc
    return [message["id"] for message in response.get("messages", [])]


def get_message(db: Session, connection: EmailConnection, gmail_message_id: str) -> dict[str, Any]:
    service = get_gmail_service(db, connection)
    try:
        return (
            service.users()
            .messages()
            .get(userId="me", id=gmail_message_id, format="full")
            .execute()
        )
    except HttpError as exc:
        raise HTTPException(status_code=400, detail="Unable to read Gmail message.") from exc


def normalize_message(raw_message: dict[str, Any]) -> dict[str, Any]:
    payload = raw_message.get("payload") or {}
    headers = _headers_to_dict(payload.get("headers") or [])
    body_preview = _extract_body_preview(payload)[:4000]
    return {
        "gmail_message_id": raw_message.get("id"),
        "thread_id": raw_message.get("threadId"),
        "subject": headers.get("subject"),
        "sender": headers.get("from"),
        "recipients": ", ".join(
            value for value in [headers.get("to"), headers.get("cc")] if value
        )
        or None,
        "snippet": raw_message.get("snippet"),
        "body_preview": body_preview,
        "received_at": _parse_received_at(headers.get("date"), raw_message.get("internalDate")),
        "has_attachments": _has_attachments(payload),
    }


def build_default_query(lookback_days: int) -> str:
    return (
        f'newer_than:{lookback_days}d '
        '(booking OR "BL draft" OR "arrival notice" OR "freight invoice" '
        'OR "delivery order" OR pre-alert OR shipment)'
    )


def _headers_to_dict(headers: list[dict[str, str]]) -> dict[str, str]:
    return {header.get("name", "").lower(): header.get("value", "") for header in headers}


def _extract_body_preview(payload: dict[str, Any]) -> str:
    if payload.get("mimeType", "").startswith("text/"):
        data = (payload.get("body") or {}).get("data")
        if data:
            return _decode_body(data)
    chunks = []
    for part in payload.get("parts") or []:
        text = _extract_body_preview(part)
        if text:
            chunks.append(text)
    return "\n".join(chunks)


def _decode_body(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _has_attachments(payload: dict[str, Any]) -> bool:
    filename = payload.get("filename")
    body = payload.get("body") or {}
    if filename or body.get("attachmentId"):
        return True
    return any(_has_attachments(part) for part in payload.get("parts") or [])


def _parse_received_at(date_header: Optional[str], internal_date: Optional[str]) -> Optional[datetime]:
    if date_header:
        try:
            return _naive_utc(parsedate_to_datetime(date_header))
        except (TypeError, ValueError, IndexError):
            pass
    if internal_date:
        try:
            return datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc).replace(tzinfo=None)
        except (TypeError, ValueError):
            return None
    return None


def _naive_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)
