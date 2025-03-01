from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from jinja2 import Environment, FileSystemLoader

from flowdapt.lib.database.base import BaseStorage
from flowdapt.lib.utils.misc import import_from_script


DEFAULT_REVISIONS_DIR = Path(__file__).parent / "revisions"


def generate_revision_id():
    """
    Generate a revision id.
    """
    return uuid4().hex[:8]


def generate_revision_script(
    revision_id: str,
    down_revision_id: str,
    revision_title: str,
    revisions_dir: Path = DEFAULT_REVISIONS_DIR,
    template_dir: str = "tpls",
) -> None:
    """
    Generate a revision script.

    :param revision_id: The revision id.
    :param down_revision_id: The down revision id.
    :param revision_title: The revision title.
    :param revisions_dir: The directory to write the revision script to.
    :param template_dir: The directory containing the revision script template.
    """
    # Convert title to snake case
    revision_title_slug = revision_title.lower().replace(" ", "_")

    filename = f"{revision_id}_{revision_title_slug}.py"
    output_path = Path(revisions_dir).absolute() / filename

    env = Environment(loader=FileSystemLoader(Path(__file__).parent / template_dir))
    template = env.get_template("revision.tpl")
    script = template.render(
        revision_id=revision_id,
        down_revision_id=down_revision_id,
        revision_title=revision_title,
    )
    output_path.write_text(script)


def generate_next_script(
    revision_title: str,
    revisions_dir: Path | str = DEFAULT_REVISIONS_DIR,
    template_dir: Path | str = "tpls",
) -> None:
    """
    Generate a revision script with the next revision id.

    :param revision_title: The revision title.
    :param revisions_dir: The directory to write the revision script to.
    :param template_dir: The directory containing the revision script template.
    """
    revision_id = generate_revision_id()
    down_revision_id = RevisionChain.from_dir(revisions_dir).head_revision

    generate_revision_script(
        revision_id=revision_id,
        down_revision_id=down_revision_id,
        revision_title=revision_title,
        revisions_dir=revisions_dir,
        template_dir=template_dir,
    )


class MigrateOp:
    def __init__(self, database: BaseStorage):
        self.database = database

    async def create_collection(self, name: str):
        """
        Create a collection.

        :param name: The name of the collection.
        """
        await self.database.create_collection(name)

    async def drop_collection(self, name: str):
        """
        Drop a collection.

        :param name: The name of the collection.
        """
        await self.database.drop_collection(name)

    async def add_field(self, collection: str, field: str, default: Any = None):
        """
        Add a field to a collection.

        :param collection: The name of the collection.
        :param field: The name of the field.
        :param default: The default value for the field.
        """
        await self.database.add_field(collection, field, default)

    async def drop_field(self, collection: str, field: str):
        """
        Drop a field from a collection.

        :param collection: The name of the collection.
        :param field: The name of the field.
        """
        await self.database.drop_field(collection, field)

    async def rename_field(self, collection: str, field: str, new_name: str):
        """
        Rename a field in a collection.

        :param collection: The name of the collection.
        :param field: The name of the field.
        :param new_name: The new name of the field.
        """
        await self.database.rename_field(collection, field, new_name)

    async def add_index(self, collection: str, field: str, unique: bool = False):
        """
        Add an index to a collection.

        :param collection: The name of the collection.
        :param field: The name of the field.
        :param unique: Whether the index should be unique.
        """
        await self.database.add_index(collection, field, unique)

    async def drop_index(self, collection: str, field: str):
        """
        Drop an index from a collection.

        :param collection: The name of the collection.
        :param field: The name of the field.
        """
        await self.database.drop_index(collection, field)


class Revision:
    def __init__(
        self,
        revision_id: str,
        down_revision_id: str,
        upgrade: Callable,
        downgrade: Callable,
    ):
        self.revision_id = revision_id
        self.down_revision_id = down_revision_id
        self.upgrade = upgrade
        self.downgrade = downgrade

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f"<Revision {self.down_revision_id} -> {self.revision_id}>"

    @classmethod
    def from_script(cls, path: Path):
        """
        Create a Revision from a revision script.
        """
        module = import_from_script(path)
        return cls(
            revision_id=module.revision_id,
            down_revision_id=module.down_revision_id,
            upgrade=module.upgrade,
            downgrade=module.downgrade,
        )


class RevisionChain:
    def __init__(self, revisions: list[Revision]):
        self.revisions = (
            {revision.revision_id: revision for revision in revisions} if revisions else {}
        )
        self.head_revision = self.get_revision_head()
        self.tail_revision = self.get_revision_tail()

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f"<RevisionChain {self.revisions}>"

    def get_revision_head(self):
        """
        Get the head revision id.
        """
        down_revisions = {
            rev.down_revision_id for rev in self.revisions.values() if rev.down_revision_id
        }
        heads = set(self.revisions) - down_revisions
        return next(iter(heads), None)

    def get_revision_tail(self):
        """
        Get the tail revision id.
        """
        up_revisions = {rev.revision_id for rev in self.revisions.values() if rev.down_revision_id}
        tails = set(self.revisions) - up_revisions
        return next(iter(tails), None)

    @classmethod
    def from_dir(cls, path: Path) -> RevisionChain:
        """
        Create a RevisionChain from a directory of revision scripts.

        :param path: The path to the directory containing the revision scripts.
        :return: A RevisionChain instance.
        """
        if not isinstance(path, Path):
            path = Path(path)

        if not path.is_dir():
            raise ValueError(f"Path {path} is not a directory.")

        revisions = []
        for file in path.glob("*.py"):
            revisions.append(Revision.from_script(file))

        return cls(revisions=revisions)

    def normalize_range(self, from_revision_id: str, to_revision_id: str) -> tuple[str, str]:
        """
        Normalize the range of revisions to upgrade or downgrade.

        :param from_revision_id: The starting revision id.
        :param to_revision_id: The ending revision id.
        :return: A tuple containing the normalized starting and ending revision ids.
        """
        match from_revision_id:
            case None | "tail":
                from_revision_id = self.tail_revision
            case "head":
                from_revision_id = self.head_revision

        match to_revision_id:
            case None | "tail":
                to_revision_id = self.tail_revision
            case "head":
                to_revision_id = self.head_revision

        return from_revision_id, to_revision_id

    def _build_graph(self, reverse: bool = False) -> dict[str, list[str]]:
        """
        Build a graph from the revisions.

        :return: A dictionary representing the graph, where each key is a revision ID
                 and each value is a list of revision IDs that can be reached from the key.
        """
        graph = defaultdict(list)

        for rev in self.revisions.values():
            if rev.down_revision_id:
                if reverse:
                    graph[rev.revision_id].append(rev.down_revision_id)
                else:
                    graph[rev.down_revision_id].append(rev.revision_id)

        return graph

    def _find_path(self, graph: dict[str, list[str]], start_id: str, end_id: str) -> list[str]:
        """
        Find a path in the graph from start_id to end_id.

        :param graph: The graph representing the revisions.
        :param start_id: The starting revision ID.
        :param end_id: The ending revision ID.
        :return: List of revision IDs representing the path from start to end.
        """
        visited = set()
        queue = [(start_id, [start_id])]

        while queue:
            (current_id, path) = queue.pop(0)

            if current_id == end_id:
                return path

            visited.add(current_id)

            for next_id in graph.get(current_id, []):
                if next_id not in visited:
                    queue.append((next_id, path + [next_id]))

        raise ValueError(f"No path found from {start_id} to {end_id}.")

    def get_chain(
        self, from_revision_id: str, to_revision_id: str, reverse: bool = False
    ) -> list[str]:
        """
        Get the chain of revisions to upgrade or downgrade.

        :param from_revision_id: The starting revision id.
        :param to_revision_id: The ending revision id.
        :param reverse: Whether to reverse the chain.
        :return: A list of revision IDs representing the chain.
        """
        if not self.revisions:
            return [], None

        from_revision_id, to_revision_id = self.normalize_range(from_revision_id, to_revision_id)

        graph = self._build_graph(reverse=reverse)
        path = self._find_path(graph, from_revision_id, to_revision_id)
        chain = [self.revisions[revision_id] for revision_id in path]

        return chain, chain[-1].revision_id if chain else None

    def get_upgrade_chain(
        self, from_revision_id: str | None, to_revision_id: str | None
    ) -> tuple[list[Callable], str]:
        """
        Get the chain of Revisions to upgrade given a range of revisions.

        :param from_revision_id: The starting revision id.
        :param to_revision_id: The ending revision id.
        :return: A tuple containing the list of upgrade functions and the target revision id.
        """
        chain, target_revision = self.get_chain(from_revision_id, to_revision_id)
        return [revision.upgrade for revision in chain], target_revision

    def get_downgrade_chain(
        self, from_revision_id: str | None, to_revision_id: str | None
    ) -> tuple[list[Callable], str]:
        """
        Get the chain of Revisions to downgrade given a range of revisions.

        :param from_revision_id: The starting revision id.
        :param to_revision_id: The ending revision id.
        :return: A tuple containing the list of downgrade functions and the target revision id.
        """
        chain, target_revision = self.get_chain(from_revision_id, to_revision_id, reverse=True)
        # Downgrade chain should be non-inclusive of the target revision
        chain = chain[:-1]
        return [revision.downgrade for revision in chain], target_revision


class Migrator:
    def __init__(self, database: BaseStorage, revisions: RevisionChain):
        self.database = database
        self.revisions = revisions

    async def upgrade(self, revision_id: str = "head"):
        """
        Upgrade the database to the given revision.
        """
        current_revision_id = await self.database.current_revision_id()

        if current_revision_id == revision_id:
            return

        upgrade_chain, target_revision = self.revisions.get_upgrade_chain(
            current_revision_id, revision_id
        )
        op = MigrateOp(self.database)

        for upgrade in upgrade_chain:
            await upgrade(op)

        await self.database.set_revision_id(target_revision)

    async def downgrade(self, revision_id: str):
        """
        Downgrade the database to the given revision.
        """
        current_revision_id = await self.database.current_revision_id()

        if current_revision_id == revision_id:
            return

        downgrade_chain, target_revision = self.revisions.get_downgrade_chain(
            current_revision_id, revision_id
        )
        op = MigrateOp(self.database)

        for downgrade in downgrade_chain:
            await downgrade(op)

        await self.database.set_revision_id(target_revision)

    @classmethod
    def from_dir(cls, database: BaseStorage, path: Path | str = DEFAULT_REVISIONS_DIR):
        """
        Create a Migrator from a directory of revision scripts.
        """
        if isinstance(path, str):
            path = Path(path)

        revisions = RevisionChain.from_dir(path)
        return cls(database, revisions)


async def run_upgrade_from_dir(
    database: BaseStorage,
    revision_id: str = "head",
    revisions_dir: Path | str = DEFAULT_REVISIONS_DIR,
):
    """
    Run the upgrade chain from the current revision to the given revision for a
    directory of revision scripts.
    """
    migrator = Migrator.from_dir(database, revisions_dir)
    await migrator.upgrade(revision_id)


async def run_downgrade_from_dir(
    database: BaseStorage,
    revision_id: str,
    revisions_dir: Path | str = DEFAULT_REVISIONS_DIR,
):
    """
    Run the downgrade chain from the current revision to the given revision for a
    directory of revision scripts.
    """
    migrator = Migrator.from_dir(database, revisions_dir)
    await migrator.downgrade(revision_id)
