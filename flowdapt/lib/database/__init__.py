from flowdapt.lib.database.base import BaseStorage
from flowdapt.lib.database.migrate import run_upgrade_from_dir
from flowdapt.lib.logger import get_logger


logger = get_logger(__name__)
_DATABASE: BaseStorage | None = None


def get_database():
    global _DATABASE
    if _DATABASE is None:
        raise RuntimeError("Database not initialized")
    return _DATABASE


async def create_database_from_config(config, *, run_migrations: bool = True) -> BaseStorage:
    global _DATABASE

    if _DATABASE is not None:
        raise RuntimeError("Database already initialized")

    _DATABASE = config.database.instantiate()
    await logger.ainfo("DatabaseInitializing", target=config.database.target)

    if run_migrations:
        await logger.ainfo("RunningMigrations", database=_DATABASE.__class__.__name__)
        try:
            async with _DATABASE:
                await run_upgrade_from_dir(_DATABASE)
                current_revision_id = await _DATABASE.current_revision_id()
        except Exception as e:
            await logger.aexception("ExceptionOccurred", error=str(e))
            raise e

        await logger.ainfo(
            "MigrationsComplete",
            current_revision=current_revision_id,
            database=_DATABASE.__class__.__name__,
        )

    await logger.ainfo("DatabaseInitialized", database=_DATABASE.__class__.__name__)

    return _DATABASE


__all__ = ("get_database", "create_database_from_config")
