from __future__ import annotations

from enum import Enum

from flowdapt.lib.context import inject_context
from flowdapt.lib.database.base import BaseStorage, Field
from flowdapt.lib.domain.models import Resource
from flowdapt.lib.utils.misc import import_from_string
from flowdapt.lib.utils.model import (
    BaseModel,
    pre_validator,
)
from flowdapt.triggers.resources.triggers.conditions import check_condition
from flowdapt.triggers.resources.triggers.cron import validate_cron_schedule


TRIGGER_RESOURCE_KIND = "trigger_rule"
ACTIONS_IMPORT_PATH = "flowdapt.triggers.resources.triggers.actions.{target}"


class TriggerRuleType(str, Enum):
    schedule = "schedule"
    condition = "condition"


class TriggerRuleAction(BaseModel):
    target: str
    parameters: dict = {}

    @pre_validator()
    @classmethod
    def validate_action(cls, values: dict):
        target = values.get("target")
        parameters = values.get("parameters")

        if not target:
            raise ValueError("Target action must be specified")

        try:
            cls.get_target_func(target)
        except ImportError:
            raise ValueError(f"Unknown action `{target}` or problems with action code.")

        if not parameters and values.get("params"):
            values["parameters"] = values.pop("params")

        return values

    @staticmethod
    def get_target_func(target: str):
        import_path = ACTIONS_IMPORT_PATH.format(target=target) if "." not in target else target
        return import_from_string(import_path)

    async def run(self):
        return await inject_context(self.get_target_func(self.target), self.parameters)()


class TriggerRuleSpec(BaseModel):
    type: TriggerRuleType = "condition"
    rule: dict | list[str]
    action: TriggerRuleAction

    @pre_validator()
    @classmethod
    def validate_rule(cls, values: dict):
        if (values.get("type") == TriggerRuleType.condition) and (
            not values.get("rule") or not isinstance(values.get("rule"), dict)
        ):
            raise ValueError("Condition rule must be a dictionary and is required")
        elif (values.get("type") == TriggerRuleType.schedule) and (
            not values.get("rule") or not isinstance(values.get("rule"), list)
        ):
            raise ValueError("Schedule rule must be a list of strings and is required")

        if values.get("type") == TriggerRuleType.schedule:
            [validate_cron_schedule(rule) for rule in values.get("rule")]

        return values

    def check_condition(self, data: dict):
        assert self.type == TriggerRuleType.condition, "Rule type must be condition"
        return check_condition(self.rule, data)


class TriggerRuleResource(Resource):
    kind: str = TRIGGER_RESOURCE_KIND
    spec: TriggerRuleSpec

    @classmethod
    async def get_scheduled(cls, database: BaseStorage) -> list[TriggerRuleResource]:
        return await database.find(cls, Field.spec.type == TriggerRuleType.schedule)

    @classmethod
    async def get_conditional(cls, database: BaseStorage) -> list[TriggerRuleResource]:
        return await database.find(cls, Field.spec.type == TriggerRuleType.condition)
