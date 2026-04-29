import redis.asyncio as redis
import logging
import json

logger = logging.getLogger(__name__)

class RedisManager:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Initialize the connection pool on app startup."""
        # Note: In production, pull the URL from your environment variables (e.g. os.getenv("REDIS_URL"))
        self.pool = redis.Redis.from_url("redis://localhost:6379/0", decode_responses=True)
        logger.info("🟢 Redis Connection Pool Initialized")

    async def disconnect(self):
        """Close the pool gracefully on app shutdown."""
        if self.pool:
            await self.pool.aclose()
            logger.info("🔴 Redis Connection Pool Closed")

    async def publish_chat_event(self, organization_id: str, conversation_id: str, message: dict):
        """Helper function to format and publish chat events cleanly."""
        if not self.pool:
            logger.error("Redis pool is not initialized!")
            return

        payload = {
            "type": "NEW_MESSAGE",
            "organizationId": str(organization_id),
            "conversationId": str(conversation_id),
            "message": message
        }
        await self.pool.publish("chat_events", json.dumps(payload))

# Create a global instance that all your services can import
redis_client = RedisManager()