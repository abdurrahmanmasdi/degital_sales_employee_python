import hmac
import hashlib
from fastapi import Request, HTTPException, status
from app.core.config import settings

async def verify_meta_signature(request: Request):
    """
    FastAPI Dependency: Verifies the HMAC SHA256 signature sent by Meta.
    Any request failing this check is immediately dropped.
    """
    signature_header = request.headers.get("X-Hub-Signature-256")
    
    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Meta signature header"
        )
    
    try:
        # Meta's header looks like: "sha256=1234567890abcdef..."
        expected_signature = signature_header.split("sha256=")[1]
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Meta signature format"
        )

    # We MUST read the raw bytes of the request to calculate the hash
    body = await request.body()

    # Calculate the expected HMAC using our secure App Secret
    calculated_hmac = hmac.new(
        key=settings.META_APP_SECRET.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256
    ).hexdigest()

    # hmac.compare_digest prevents "timing attacks" from hackers
    if not hmac.compare_digest(expected_signature, calculated_hmac):
        print("🔴 SECURITY ALERT: Blocked unauthorized webhook attempt!")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Meta signature"
        )
    
    return True