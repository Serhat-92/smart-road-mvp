"""Shared event contract validation for known event payloads."""

from app.core.pydantic import model_to_dict
from event_contracts import DetectionEvent, FusedVehicleEvent, SpeedViolationAlert


KNOWN_EVENT_CONTRACTS = {
    "detection.event": DetectionEvent,
    "fused.vehicle_event": FusedVehicleEvent,
    "speed.violation_alert": SpeedViolationAlert,
}


class EventContractValidator:
    """Validates shared event payloads while keeping unknown event types flexible."""

    def __init__(self, contract_models: dict[str, type] | None = None):
        self.contract_models = contract_models or KNOWN_EVENT_CONTRACTS

    def validate(self, event_type: str, payload: dict) -> dict:
        contract_model = self.contract_models.get(event_type)
        if contract_model is None:
            return payload

        validated_contract = contract_model(**payload)
        return model_to_dict(validated_contract)
