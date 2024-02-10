from flowdapt.lib.database.migrate import MigrateOp
from datetime import datetime

revision_id = "3a59d747"
down_revision_id = "50bfe794"


async def upgrade(op: MigrateOp):
    print("Running upgrade on Revision 2")
    await op.add_field("Group", "updated_at", default=datetime.now())


async def downgrade(op: MigrateOp):
    print("Running downgrade on Revision 2")
    await op.drop_field("Group", "updated_at")
