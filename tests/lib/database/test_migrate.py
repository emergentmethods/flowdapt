import pytest
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field as PydanticField
from datetime import datetime

from flowdapt.lib.database.base import Document
from flowdapt.lib.database.migrate import Migrator, Revision, RevisionChain, MigrateOp
from flowdapt.lib.database.storage.memory import InMemoryStorage


class Permission(BaseModel):
    type: str
    level: int = PydanticField(ge=0, default=25)

class Group(Document):
    name: str
    permissions: list[Permission] = []
    labels: dict[str, str] = {}
    created_at: datetime = PydanticField(default_factory=datetime.utcnow)

groups = [
    Group(name="Admin", permissions=[Permission(type="read", level=100), Permission(type="write", level=100)], labels={"role": "admin"}),
    Group(name="User", permissions=[Permission(type="read", level=50)], labels={"role": "user"}),
    Group(name="Moderator", permissions=[Permission(type="read", level=75), Permission(type="write", level=50)], labels={"role": "moderator"}),
]


@pytest.fixture
async def database():
    async with InMemoryStorage() as database:
        yield database


async def test_migration_basic_revision(database: InMemoryStorage):
    async def upgrade(op: MigrateOp):
        await op.create_collection("test")
    
    async def downgrade(op: MigrateOp):
        await op.drop_collection("test")

    revision = Revision(
        revision_id="1",
        down_revision_id=None,
        upgrade=upgrade,
        downgrade=downgrade,
    )

    migrator = Migrator(database, RevisionChain([revision]))
    await migrator.upgrade()

    assert "test" in database._storage


async def test_migration_get_head_revision(database: InMemoryStorage):
    async def upgrade(op: MigrateOp):
        await op.create_collection("test")
    
    async def downgrade(op: MigrateOp):
        await op.drop_collection("test")

    revision = Revision(
        revision_id="1",
        down_revision_id=None,
        upgrade=upgrade,
        downgrade=downgrade,
    )

    chain = RevisionChain([revision])
    assert chain.get_revision_head() == "1"

    revision_two = Revision(
        revision_id="2",
        down_revision_id="1",
        upgrade=upgrade,
        downgrade=downgrade,
    )

    chain = RevisionChain([revision, revision_two])
    assert chain.get_revision_head() == "2"

    revision_three = Revision(
        revision_id="3",
        down_revision_id="2",
        upgrade=upgrade,
        downgrade=downgrade,
    )

    chain = RevisionChain([revision, revision_two, revision_three])
    assert chain.get_revision_head() == "3"


async def test_migration_get_chain(database: InMemoryStorage):
    async def upgrade(op: MigrateOp):
        await op.create_collection("test")
    
    async def downgrade(op: MigrateOp):
        await op.drop_collection("test")

    revision = Revision(
        revision_id="1",
        down_revision_id=None,
        upgrade=upgrade,
        downgrade=downgrade,
    )
    revision_two = Revision(
        revision_id="2",
        down_revision_id="1",
        upgrade=upgrade,
        downgrade=downgrade,
    )
    revision_three = Revision(
        revision_id="3",
        down_revision_id="2",
        upgrade=upgrade,
        downgrade=downgrade,
    )

    chain = RevisionChain([revision, revision_two, revision_three])
    assert chain.get_chain(None, "head") == ([revision, revision_two, revision_three], "3")
    assert chain.get_chain(None, "3") == ([revision, revision_two, revision_three], "3")
    assert chain.get_chain(None, "1") == ([revision], "1")


async def test_migration_get_upgrade_chain(database: InMemoryStorage):
    async def upgrade(op: MigrateOp):
        await op.create_collection("test")
    
    async def downgrade(op: MigrateOp):
        await op.drop_collection("test")

    revision = Revision(
        revision_id="1",
        down_revision_id=None,
        upgrade=upgrade,
        downgrade=downgrade,
    )
    revision_two = Revision(
        revision_id="2",
        down_revision_id="1",
        upgrade=upgrade,
        downgrade=downgrade,
    )
    revision_three = Revision(
        revision_id="3",
        down_revision_id="2",
        upgrade=upgrade,
        downgrade=downgrade,
    )

    chain = RevisionChain([revision, revision_two, revision_three])
    assert chain.get_upgrade_chain(None, "head") == ([revision.upgrade, revision_two.upgrade, revision_three.upgrade], "3")
    assert chain.get_upgrade_chain(None, "3") == ([revision.upgrade, revision_two.upgrade, revision_three.upgrade], "3")
    assert chain.get_upgrade_chain(None, "1") == ([revision.upgrade], "1")


async def test_migration_get_downgrade_chain(database: InMemoryStorage):
    async def upgrade(op: MigrateOp):
        await op.create_collection("test")
    
    async def downgrade(op: MigrateOp):
        await op.drop_collection("test")

    revision = Revision(
        revision_id="1",
        down_revision_id=None,
        upgrade=upgrade,
        downgrade=downgrade,
    )
    revision_two = Revision(
        revision_id="2",
        down_revision_id="1",
        upgrade=upgrade,
        downgrade=downgrade,
    )
    revision_three = Revision(
        revision_id="3",
        down_revision_id="2",
        upgrade=upgrade,
        downgrade=downgrade,
    )

    chain = RevisionChain([revision, revision_two, revision_three])
    await database.set_revision_id("3")

    assert chain.get_downgrade_chain("head", None) == ([revision_three.downgrade, revision_two.downgrade], "1")
    assert chain.get_downgrade_chain("3", None) == ([revision_three.downgrade, revision_two.downgrade], "1")
    assert chain.get_downgrade_chain("1", None) == ([], "1")


async def test_migration_empty_chain(database: InMemoryStorage):
    chain = RevisionChain([])
    assert chain.get_revision_head() == None
    assert chain.get_revision_tail() == None
    assert chain.get_chain(None, "head") == ([], None)
    assert chain.get_upgrade_chain(None, "head") == ([], None)
    assert chain.get_downgrade_chain("head", None) == ([], None)


async def test_migration_from_dir(database: InMemoryStorage):
    migrator = Migrator.from_dir(database, path=Path(__file__).parent / "test_revisions")
    await migrator.upgrade()

    assert "Group" in database._storage


async def test_migration_with_previous_data(database: InMemoryStorage):
    await database.insert(groups)

    migrator = Migrator.from_dir(database, path=Path(__file__).parent / "test_revisions")
    await migrator.upgrade()

    assert "Group" in database._storage
    assert len(database._storage["Group"]) == 3
    assert all("updated_at" in group for group in database._storage["Group"].values())


async def test_migration_downgrade(database: InMemoryStorage):
    migrator = Migrator.from_dir(database, path=Path(__file__).parent / "test_revisions")
    await migrator.upgrade()
    await migrator.downgrade("50bfe794")

    assert "Group" in database._storage
    assert all("updated_at" not in group for group in database._storage["Group"].values())