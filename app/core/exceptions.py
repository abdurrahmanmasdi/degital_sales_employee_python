from fastapi import HTTPException, status

class TenantNotFoundError(HTTPException):
    def __init__(self, phone_number: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"No active organization found for WhatsApp number: {phone_number}"
        )

class WebhookProcessingError(HTTPException):
    def __init__(self, detail: str = "Failed to process WhatsApp webhook"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=detail
        )