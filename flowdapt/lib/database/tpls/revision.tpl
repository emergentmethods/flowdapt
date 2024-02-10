# Automatically generated
# pylint: disable=missing-module-docstring,missing-function-docstring
# flake8: noqa

"""{{ revision_title }}"""

from flowdapt.lib.database.migrate import MigrateOp

revision_id = "{{ revision_id }}"
down_revision_id = {% if down_revision_id == None %}None{% else %}"{{ down_revision_id }}"{% endif %}


async def upgrade(op: MigrateOp):
    pass


async def downgrade(op: MigrateOp):
    pass