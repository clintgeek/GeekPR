import hashlib
import hmac
import pytest
from app.core.security import verify_webhook_signature


def test_valid_signature():
    """Valid webhook signature should pass verification."""
    secret = "test-secret"
    payload = b"test payload"
    
    # Generate valid signature
    expected_hash = hmac.new(
        secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()
    signature = f"sha256={expected_hash}"
    
    # Temporarily set the secret for testing
    from app.core import config
    original_secret = config.settings.github_webhook_secret
    config.settings.github_webhook_secret = secret
    
    try:
        result = verify_webhook_signature(payload, signature)
        assert result is True
    finally:
        config.settings.github_webhook_secret = original_secret


def test_invalid_signature():
    """Invalid webhook signature should fail verification."""
    payload = b"test payload"
    signature = "sha256=invalid"
    
    result = verify_webhook_signature(payload, signature)
    assert result is False


def test_missing_signature():
    """Missing signature should fail verification."""
    payload = b"test payload"
    result = verify_webhook_signature(payload, "")
    assert result is False


def test_wrong_algorithm():
    """Wrong algorithm prefix should fail verification."""
    payload = b"test payload"
    signature = "sha1=somehash"
    
    result = verify_webhook_signature(payload, signature)
    assert result is False
