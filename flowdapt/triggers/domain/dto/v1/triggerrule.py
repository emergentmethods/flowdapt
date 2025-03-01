from enum import Enum

from flowdapt.lib.domain.dto.v1.base import V1Alpha1ResourceMetadata
from flowdapt.lib.utils.model import BaseModel, model_dump
from flowdapt.triggers.domain.models.triggerrule import (
    TRIGGER_RESOURCE_KIND,
    TriggerRuleResource,
)


class V1Alpha1TriggerRuleType(str, Enum):
    schedule = "schedule"
    condition = "condition"


class V1Alpha1TriggerRuleAction(BaseModel):
    target: str
    parameters: dict = {}


class V1Alpha1TriggerRuleResourceSpec(BaseModel):
    type: V1Alpha1TriggerRuleType = "condition"
    rule: dict | list[str]
    action: V1Alpha1TriggerRuleAction


class V1Alpha1TriggerRuleResourceBase(BaseModel):
    kind: str = TRIGGER_RESOURCE_KIND
    metadata: V1Alpha1ResourceMetadata
    spec: V1Alpha1TriggerRuleResourceSpec


class V1Alpha1TriggerRuleResourceCreateRequest(V1Alpha1TriggerRuleResourceBase):
    def to_model(self) -> TriggerRuleResource:
        return TriggerRuleResource(
            # Explicitly ignore internally populated fields
            **model_dump(self, exclude={"metadata": {"uid", "created_at", "updated_at"}}),
        )


class V1Alpha1TriggerRuleResourceCreateResponse(V1Alpha1TriggerRuleResourceBase):
    @classmethod
    def from_model(cls, model: TriggerRuleResource):
        return cls(**model_dump(model))


class V1Alpha1TriggerRuleResourceUpdateRequest(V1Alpha1TriggerRuleResourceBase):
    def to_model(self) -> TriggerRuleResource:
        return TriggerRuleResource(
            # Explicitly ignore internally populated fields
            **model_dump(self, exclude={"metadata": {"updated_at"}}),
        )


class V1Alpha1TriggerRuleResourceUpdateResponse(V1Alpha1TriggerRuleResourceCreateResponse): ...


class V1Alpha1TriggerRuleResourceReadResponse(V1Alpha1TriggerRuleResourceBase):
    @classmethod
    def from_model(cls, model: TriggerRuleResource):
        return cls(**model_dump(model))


if __name__ == "__main__":
    condition = """
{
  "&&": [
    {"==": [{"$": "type"}, "create"]},
    {"==": [{"$": "kind"}, "pod"]}
  ]
}
"""

    print(
        V1Alpha1TriggerRuleResourceCreateRequest(
            kind="trigger",
            metadata={
                "name": "test",
            },
            spec={
                "condition": condition,
                "action": {"target": "print_event", "parameters": {"test": "test"}},
            },
        )
    )
