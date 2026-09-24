from uuid import UUID

import httpx
from pydantic import ValidationError

from app.schemas.automation_events import (
    AIEventClaimResponse,
    AutomationEventClaimResponse,
    AutomationEventDeliveryResponse,
)


class AutomationEventOperationError(Exception):
    pass


class AutomationEventConflictError(Exception):
    pass


class AutomationEventService:
    def __init__(self, client):
        self.client = client

    def claim(self, event_types: list[str], limit: int) -> AutomationEventClaimResponse:
        try:
            return AutomationEventClaimResponse.model_validate(
                {"events": self.client.claim_automation_events(event_types, limit)}
            )
        except ValueError as error:
            raise AutomationEventConflictError() from error
        except (KeyError, TypeError, ValidationError, httpx.HTTPError) as error:
            raise AutomationEventOperationError() from error

    def claim_ai_summary_events(self, limit: int) -> AIEventClaimResponse:
        try:
            return AIEventClaimResponse.model_validate(
                {"events": self.client.claim_ai_summary_events(limit)}
            )
        except ValueError as error:
            raise AutomationEventConflictError() from error
        except (KeyError, TypeError, ValidationError, httpx.HTTPError) as error:
            raise AutomationEventOperationError() from error

    def complete(self, event_id: UUID) -> AutomationEventDeliveryResponse:
        return self._settle("complete_automation_event", event_id)

    def fail(self, event_id: UUID, error_message: str) -> AutomationEventDeliveryResponse:
        try:
            result = self.client.fail_automation_event(str(event_id), error_message)
            return AutomationEventDeliveryResponse.model_validate(result)
        except ValueError as error:
            raise AutomationEventConflictError() from error
        except (KeyError, TypeError, ValidationError, httpx.HTTPError) as error:
            raise AutomationEventOperationError() from error

    def _settle(self, method_name: str, event_id: UUID) -> AutomationEventDeliveryResponse:
        try:
            result = getattr(self.client, method_name)(str(event_id))
            return AutomationEventDeliveryResponse.model_validate(result)
        except ValueError as error:
            raise AutomationEventConflictError() from error
        except (KeyError, TypeError, ValidationError, httpx.HTTPError) as error:
            raise AutomationEventOperationError() from error
