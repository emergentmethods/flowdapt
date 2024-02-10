import pytest
import asyncio
from pydantic import BaseModel, Field as PydanticField
from datetime import datetime

from flowdapt.lib.utils.model import model_dump
from flowdapt.lib.database.base import Document, Field
from flowdapt.lib.database.storage.memory import InMemoryStorage

class Permission(BaseModel):
    type: str
    level: int = PydanticField(ge=0, default=25)

class Group(Document):
    name: str
    permissions: list[Permission] = []
    labels: dict[str, str] = {}
    created_at: datetime = PydanticField(default_factory=datetime.utcnow)


@pytest.fixture
async def access_control_database():
    async with InMemoryStorage() as database:
        groups = [
            Group(name="Admin", permissions=[Permission(type="read", level=100), Permission(type="write", level=100)], labels={"role": "admin"}),
            Group(name="User", permissions=[Permission(type="read", level=50)], labels={"role": "user"}),
            Group(name="Moderator", permissions=[Permission(type="read", level=75), Permission(type="write", level=50)], labels={"role": "moderator"}),
        ]
        await database.insert(groups)
        yield database

async def test_insertion_of_new_group_entity(access_control_database: InMemoryStorage):
    new_group = Group(name="Guest", permissions=[Permission(type="read")], labels={"role": "guest"})
    await access_control_database.insert([new_group])

    stored_group = access_control_database._storage[Group.collection_name].get(new_group._doc_id_)
    assert stored_group is not None
    assert stored_group["name"] == "Guest"
    assert stored_group["permissions"] == [model_dump(permission) for permission in new_group.permissions]
    assert stored_group["labels"] == new_group.labels

async def test_retrieval_of_admin_group_entity(access_control_database: InMemoryStorage):
    admin_group = await access_control_database.find(Group, Field.name == "Admin")
    assert len(admin_group) == 1
    admin_group = admin_group[0]
    assert admin_group.name == "Admin"
    assert len(admin_group.permissions) == 2
    assert admin_group.labels == {"role": "admin"}

async def test_deletion_of_moderator_group_entity(access_control_database: InMemoryStorage):
    moderator_group, *_ = await access_control_database.find(Group, Field.name == "Moderator")
    await access_control_database.delete([moderator_group])
    
    remaining_groups = await access_control_database.find(Group, Field.name == "Moderator")
    assert len(remaining_groups) == 0

async def test_modification_of_user_group_entity(access_control_database: InMemoryStorage):
    user_groups = await access_control_database.find(Group, Field.name == "User")
    assert len(user_groups) == 1
    
    user_group = user_groups[0]
    user_group.permissions.append(Permission(type="write"))  # Grant 'write' permission
    await access_control_database.update([user_group])
    
    updated_user_group = await access_control_database.find(Group, Field.name == "User")
    assert len(updated_user_group) == 1
    assert updated_user_group[0].permissions == user_group.permissions

async def test_conjunctive_query_for_admin_with_write_permission(access_control_database: InMemoryStorage):
    admin_with_write_permission = await access_control_database.find(
        Group, (Field.name == "Admin") & (Field.permissions.any_of(Field.type == "write"))
    )
    assert len(admin_with_write_permission) == 1
    assert admin_with_write_permission[0].name == "Admin"
    assert any(permission.type == "write" for permission in admin_with_write_permission[0].permissions)

async def test_disjunctive_query_for_groups_with_read_or_write_permission(access_control_database: InMemoryStorage):
    groups_with_permissions = await access_control_database.find(
        Group, (Field.permissions.any_of(Field.type == "read", Field.type == "write"))
    )
    # Assuming that all groups have at least read or write permissions
    assert len(groups_with_permissions) == len(access_control_database._storage[Group.collection_name])

    alt_groups_with_permissions = await access_control_database.find(
        Group, (Field.permissions.any_of(Field.type == "read")) | (Field.permissions.any_of(Field.type == "write"))
    )

    assert len(groups_with_permissions) == len(alt_groups_with_permissions)

async def test_query_for_user_group_with_specific_label(access_control_database: InMemoryStorage):
    user_group_with_label = await access_control_database.find(
        Group, (Field.name == "User") & (Field.labels["role"] == "user")
    )
    assert len(user_group_with_label) == 1
    assert user_group_with_label[0].labels["role"] == "user"

async def test_not_equals_query(access_control_database: InMemoryStorage):
    non_admin_groups = await access_control_database.find(Group, Field.name != "Admin")
    # Assuming that there are at least 2 groups that are not admin
    assert len(non_admin_groups) > 1
    for group in non_admin_groups:
        assert group.name != "Admin"

async def test_in_query_on_group_name(access_control_database: InMemoryStorage):
    group_names = ["Admin", "User", "NonExistentGroup"]
    groups_in_list = await access_control_database.find(
        Group, Field.name.one_of(group_names)
    )
    # Assuming 'NonExistentGroup' does not exist, there should be 2 valid groups
    assert len(groups_in_list) == 2
    for group in groups_in_list:
        assert group.name in group_names

async def test_not_in_query_on_group_name(access_control_database: InMemoryStorage):
    group_names = ["Admin", "User"]
    groups_not_in_list = await access_control_database.find(
        Group, ~Field.name.one_of(group_names)
    )
    # Assuming there are other groups apart from 'Admin' and 'User'
    assert len(groups_not_in_list) > 0
    for group in groups_not_in_list:
        assert group.name not in group_names

async def test_matches_query_with_regex(access_control_database: InMemoryStorage):
    # Assuming the 'matches' operator is implemented to use regex patterns
    groups_with_a_in_name = await access_control_database.find(
        Group, Field.name.matches(r".*a.*")
    )
    # Assuming at least one group with 'a' in its name exists
    assert len(groups_with_a_in_name) > 0
    for group in groups_with_a_in_name:
        assert 'a' in group.name

async def test_exists_query_on_permissions_field(access_control_database: InMemoryStorage):
    groups_with_permissions = await access_control_database.find(
        Group, Field.permissions.exists()
    )
    # Assuming all groups have permissions defined
    assert len(groups_with_permissions) == len(access_control_database._storage[Group.collection_name])

async def test_and_query_combining_multiple_conditions(access_control_database: InMemoryStorage):
    # Groups with 'read' permission and label 'role' as 'user'
    groups_with_conditions = await access_control_database.find(
        Group, (Field.permissions.any_of(Field.type == "read")) & (Field.labels["role"] == "user")
    )
    assert len(groups_with_conditions) > 0
    for group in groups_with_conditions:
        assert any(permission.type == "read" for permission in group.permissions)
        assert group.labels["role"] == "user"

async def test_or_query_combining_multiple_conditions(access_control_database: InMemoryStorage):
    # Groups with 'write' permission or name 'User'
    groups_with_conditions = await access_control_database.find(
        Group, (Field.permissions.any_of(Field.type == "write")) | (Field.name == "User")
    )
    assert len(groups_with_conditions) > 0

async def test_insertion_of_new_group_entity_with_transaction(access_control_database: InMemoryStorage):
    new_group = Group(name="Guest", permissions=[Permission(type="read")], labels={"role": "guest"})

    # Start a transaction
    async with access_control_database.transaction():
        await access_control_database.insert([new_group])

    # Once the transaction context is exited, the commit should have happened.
    stored_group = await access_control_database.get(Group, new_group._doc_id_)
    assert stored_group is not None
    assert stored_group.name == "Guest"
    assert stored_group.permissions == new_group.permissions
    assert stored_group.labels == new_group.labels

async def test_deletion_of_moderator_group_entity_with_transaction(access_control_database: InMemoryStorage):
    moderator_group = await access_control_database.find_one(Group, Field.name == "Moderator")

    # Start a transaction
    async with access_control_database.transaction():
        await access_control_database.delete([moderator_group])

    # Check if the delete operation was successful
    remaining_groups = await access_control_database.find(Group, Field.name == "Moderator")
    assert len(remaining_groups) == 0

async def test_modification_of_user_group_entity_with_transaction(access_control_database: InMemoryStorage):
    user_group = await access_control_database.find_one(Group, Field.name == "User")
    user_group.permissions.append(Permission(type="write"))  # Grant 'write' permission

    # Start a transaction
    async with access_control_database.transaction():
        await access_control_database.update([user_group])

    # Check if the update operation was successful
    updated_user_group = await access_control_database.find_one(Group, Field.name == "User")
    assert updated_user_group.permissions == user_group.permissions

async def test_rollback_on_error(access_control_database: InMemoryStorage):
    initial_groups = await access_control_database.get_all(Group)

    new_group = Group(name="Temporary", permissions=[Permission(type="read")], labels={"role": "temp"})

    try:
        # Start a transaction
        async with access_control_database.transaction():
            await access_control_database.insert([new_group])
            # Force an error
            raise Exception("Forced exception to test rollback")
    except Exception:
        pass

    # Check if the rollback was successful
    groups_after_rollback = await access_control_database.get_all(Group)
    assert len(groups_after_rollback) == len(initial_groups)
    assert all(group.name != "Temporary" for group in groups_after_rollback)


async def test_atomicity_of_transactions(access_control_database: InMemoryStorage):
    initial_groups = await access_control_database.get_all(Group)

    new_group_1 = Group(name="Atomic1", permissions=[Permission(type="read")], labels={"role": "atomic"})
    new_group_2 = Group(name="Atomic2", permissions=[Permission(type="write")], labels={"role": "atomic"})

    # Start a transaction
    async with access_control_database.transaction():
        await access_control_database.insert([new_group_1])
        await access_control_database.insert([new_group_2])

    # Check if both operations within the transaction have been committed
    groups_after_insertion = await access_control_database.get_all(Group)
    assert len(groups_after_insertion) == len(initial_groups) + 2
    assert any(group.name == "Atomic1" for group in groups_after_insertion)
    assert any(group.name == "Atomic2" for group in groups_after_insertion)

async def test_concurrent_inserts(access_control_database: InMemoryStorage):
    new_group_1 = Group(name="Concurrent1", permissions=[Permission(type="read")], labels={"role": "concurrent"})
    new_group_2 = Group(name="Concurrent2", permissions=[Permission(type="write")], labels={"role": "concurrent"})

    async def insert_group(group):
        async with access_control_database.transaction():
            await access_control_database.insert([group])

    # Run two coroutines concurrently
    await asyncio.gather(
        insert_group(new_group_1),
        insert_group(new_group_2)
    )

    # After both inserts, check if the database has the correct number of new groups
    groups_after_insertion = await access_control_database.get_all(Group)
    assert len([group for group in groups_after_insertion if group.name.startswith("Concurrent")]) == 2

async def test_concurrent_updates(access_control_database: InMemoryStorage):
    group_to_update = await access_control_database.find_one(Group, Field.name == "User")
    group_to_update.permissions.append(Permission(type="write"))

    async def update_group(group):
        async with access_control_database.transaction():
            await access_control_database.update([group])

    # Run two coroutines concurrently
    await asyncio.gather(
        update_group(group_to_update),
        update_group(group_to_update)
    )

    # After both updates, check if the database has the correct number of new groups
    updated_group = await access_control_database.find_one(Group, Field.name == "User")
    assert len(updated_group.permissions) == 2

async def test_concurrent_deletes(access_control_database: InMemoryStorage):
    group_to_delete = await access_control_database.find_one(Group, Field.name == "User")

    async def delete_group(group):
        async with access_control_database.transaction():
            await access_control_database.delete([group])

    # Run two coroutines concurrently
    await asyncio.gather(
        delete_group(group_to_delete),
        delete_group(group_to_delete)
    )

    # After both deletes, check if the database has the correct number of new groups
    remaining_groups = await access_control_database.find(Group, Field.name == "User")
    assert len(remaining_groups) == 0

async def test_list_collections(access_control_database: InMemoryStorage):
    collections = await access_control_database.list_collections()
    assert len(collections) == 1
    assert collections[0] == Group.collection_name