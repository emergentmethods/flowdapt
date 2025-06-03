import typer
from asyncer import runnify

from flowdapt.lib.utils.asynctools import is_async_callable


class AsyncTyper(typer.Typer):
    """
    Custom Typer object to facilitate running async commands.
    """

    def command(self, *args, **kwargs):
        # Run async commands
        decorator = super().command(*args, **kwargs)

        def wrapper(fn):
            if is_async_callable(fn):
                fn = runnify(fn)
            return decorator(fn)
        return wrapper

    def callback(self, *args, **kwargs):
        # Run async callbacks
        decorator = super().callback(*args, **kwargs)

        def wrapper(fn):
            if is_async_callable(fn):
                fn = runnify(fn)
            return decorator(fn)
        return wrapper
