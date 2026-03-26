import hashlib
import hmac

from app.core.config import settings


def verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Verify that the webhook payload was sent by GitHub.

    Args:
        payload_body: The raw bytes of the request body.
        signature_header: The value of the X-Hub-Signature-256 header.

    Returns:
        True if the signature is valid, False otherwise.
    """
    if not signature_header:
        return False

    expected_signature = (
        "sha256="
        + hmac.new(
            settings.github_webhook_secret.encode("utf-8"),
            msg=payload_body,
            digestmod=hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(expected_signature, signature_header)
