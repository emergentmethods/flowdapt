# Automatically generated
# pylint: disable=missing-module-docstring,missing-function-docstring
# flake8: noqa

"""initial setup"""

from flowdapt.lib.database.migrate import MigrateOp

from flowdapt.compute.domain.models.workflow import WorkflowResource
from flowdapt.compute.domain.models.workflowrun import WorkflowRun
from flowdapt.compute.domain.models.config import ConfigResource
from flowdapt.triggers.domain.models.triggerrule import TriggerRuleResource

revision_id = "cec3ffd4"
down_revision_id = None



async def upgrade(op: MigrateOp):
    await op.create_collection(WorkflowResource.collection_name)
    await op.create_collection(WorkflowRun.collection_name)
    await op.create_collection(ConfigResource.collection_name)
    await op.create_collection(TriggerRuleResource.collection_name)

    await op.add_index(WorkflowResource.collection_name, "metadata.name", unique=True)
    await op.add_index(WorkflowResource.collection_name, "metadata.uid", unique=True)
    await op.add_index(ConfigResource.collection_name, "metadata.name", unique=True)
    await op.add_index(ConfigResource.collection_name, "metadata.uid", unique=True)
    await op.add_index(TriggerRuleResource.collection_name, "metadata.name", unique=True)
    await op.add_index(TriggerRuleResource.collection_name, "metadata.uid", unique=True)
    await op.add_index(WorkflowRun.collection_name, "name", unique=True)
    await op.add_index(WorkflowRun.collection_name, "uid", unique=True)

async def downgrade(op: MigrateOp):
    await op.drop_collection(WorkflowResource.collection_name)
    await op.drop_collection(WorkflowRun.collection_name)
    await op.drop_collection(ConfigResource.collection_name)
    await op.drop_collection(TriggerRuleResource.collection_name)
