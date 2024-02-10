from flowdapt.lib.database.migrate import MigrateOp

revision_id = "50bfe794"
down_revision_id = None


async def upgrade(op: MigrateOp):
    print("Running upgrade on Revision 1")
    await op.create_collection("Group")


async def downgrade(op: MigrateOp):
    print("Running downgrade on Revision 1")
    await op.drop_collection("Group")