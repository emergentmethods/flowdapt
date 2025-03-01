from datetime import datetime

from crontab import CronTab


def validate_cron_schedule(schedule: str):
    """
    Validate a schedule string for CronTab.

    :raises: ValueError if invalid
    """
    try:
        CronTab(schedule)
    except ValueError:
        raise
    except BaseException:
        pass


def is_ready_to_run(
    next_run_time: datetime, last_run_time: datetime, now: datetime | None = None
) -> bool:
    """
    Determines whether a cron is ready to run based on its next scheduled run time,
    the time it was last run, and the current time.

    :param next_run_time: A datetime object representing the next scheduled run time for the cron.
    :param last_run_time: A datetime object representing the time the cron was last run.
    :param now: A datetime object representing the current time.
    :return: True if the cron is ready to run now, False otherwise.
    """
    now = now or datetime.utcnow()
    if next_run_time <= now and last_run_time < next_run_time:
        return True
    else:
        return False


def get_next_run_datetime(cron_schedule: str, now: datetime | None = None) -> datetime:
    """
    Given a cron schedule, determine the next datetime to run.

    :param cron_schedule: The cron schedule string
    :type cron_schedule: str
    :param now: A datetime object representing the current time
    :type now: datetime
    :return: The datetime object to run the cron next
    """
    now = now or datetime.utcnow()
    return CronTab(cron_schedule).next(now=now, return_datetime=True, default_utc=False)
