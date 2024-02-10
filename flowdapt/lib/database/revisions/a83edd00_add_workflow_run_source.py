# Automatically generated
# pylint: disable=missing-module-docstring,missing-function-docstring
# flake8: noqa

"""Add workflow run source"""

from flowdapt.lib.database.migrate import MigrateOp

revision_id = "a83edd00"
down_revision_id = "cec3ffd4"


async def upgrade(op: MigrateOp):
    await op.add_field(
        collection="WorkflowRun",
        field="source",
        default=None,
    )


async def downgrade(op: MigrateOp):
    await op.drop_field(
        collection="WorkflowRun",
        field="source"
    )