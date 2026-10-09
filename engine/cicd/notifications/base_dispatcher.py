"""Base Abstract Notification Dispatcher."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseNotificationDispatcher(ABC):
    @abstractmethod
    async def send_notification(
        self,
        target_url: str,
        title: str,
        payload: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Dispatches notification payload to target destination. Returns True if successful."""
        pass
