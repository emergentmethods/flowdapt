import asyncio
import subprocess
import sys
from contextlib import asynccontextmanager
from functools import cache, partial, wraps
from pathlib import Path
from typing import (
    Any,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    ParamSpec,
    Protocol,
    Tuple,
    TypeVar,
    runtime_checkable,
)

from aiosonic import HTTPClient
from asynctempfile import NamedTemporaryFile


T = TypeVar("T")
P = ParamSpec("P")
R = TypeVar("R")

CallableType = Callable[..., R] | Callable[..., Awaitable[R]]  # type: ignore


@runtime_checkable
class AsyncFileLikeObject(Protocol):
    async def read(self, n: int = -1) -> bytes: ...

    async def write(self, data: bytes) -> None | int: ...

    async def close(self) -> None: ...


def is_async_callable(f: CallableType) -> bool:
    """
    Test if the callable is an async callable

    :param f: The callable to test
    """
    from inspect import iscoroutinefunction

    if hasattr(f, "__wrapped__"):
        f = f.__wrapped__

    return iscoroutinefunction(f)


def is_async_context_manager(o: Any) -> bool:
    """
    Test if object is an async context manager

    :param o: The object to check
    """
    return hasattr(o, "__aenter__") and hasattr(o, "__aexit__")


async def run_in_thread(callable: Callable, *args, **kwargs):
    """
    Run a sync callable in a the default ThreadPool.

    :param callable: The callable to run
    :param *args: The args to pass to the callable
    :param **kwargs: The kwargs to pass to the callable
    :returns: The return value of the callable
    """
    return await asyncio.get_running_loop().run_in_executor(
        None, partial(callable, *args, **kwargs)
    )


async def cancel_task(task: asyncio.Task):
    """
    Cancel an asyncio task and wait for it to finish.

    :param task: The task to cancel
    """
    if not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def async_cache(func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]:
    """
    Cache the result of an async function.

    :param func: async function to cache
    :return: async function
    """
    _cache = {}

    @cache
    def _make_key(*args, **kwargs) -> Tuple[Any, frozenset[Any]]:
        return (args, frozenset(kwargs.items()))

    @wraps(func)
    async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        key = _make_key(*args, **kwargs)
        if key not in _cache:
            _cache[key] = await func(*args, **kwargs)
        return _cache[key]

    return _wrapper


async def download_file(
    url: str,
    output_dir: str | Path,
    headers: dict[str, str] | None = None,
    progress_callback: Callable[[int, int], Any] | None = None,
):
    """
    Download a file from a url

    :param url: The url to download from
    :param output_path: The path to save the file to
    """
    from flowdapt.lib.utils.misc import get_filename_from_url

    async with HTTPClient() as client:
        response = await client.get(url, headers=headers or {})

        if response.status_code != 200:
            raise Exception(f"Failed to download {url}, status_code: {response.status_code}")

        total, downloaded = int(response.headers["content-length"]), 0

        output_path = Path(output_dir) / get_filename_from_url(url)

        with output_path.open("wb") as file:
            if response.chunked:
                async for chunk in response.read_chunks():
                    downloaded += await run_in_thread(file.write, chunk)
            else:
                downloaded += await run_in_thread(file.write, await response.content())

            if progress_callback:
                progress_callback(downloaded, total)

    return output_path


@asynccontextmanager
async def temp_file_from_upload(uploaded_file: AsyncFileLikeObject):
    """
    Create a temporary file from an uploaded file and yield the path.
    """

    async with NamedTemporaryFile() as tmpf:
        with Path(tmpf.name).open("wb") as f:
            while chunk := await uploaded_file.read(1024):
                f.write(chunk)

        yield tmpf.name


async def aenumerate(aiterable: AsyncIterable[T]) -> AsyncIterator[Tuple[int, T]]:
    """
    Enumerate over an asynchronous iterable

    :param aiterable: The iterable to enumerate
    """
    i = 0
    async for x in aiterable:
        yield i, x
        i += 1


async def aslice(aiterable: AsyncIterable[T | None], *args) -> AsyncIterator[T | None]:
    """
    Slice an asynchronous iterable

    :param aiterable: The iterable to slice
    :param *args: The slice args
    """
    s = slice(*args)
    it = iter(range(s.start or 0, s.stop or sys.maxsize, s.step or 1))
    try:
        nexti = next(it)
    except StopIteration:
        return
    async for i, element in aenumerate(aiterable):
        if i == nexti:
            yield element
            try:
                nexti = next(it)
            except StopIteration:
                return


async def achunk(aiterator: AsyncIterable[T | None], n: int) -> AsyncIterator[list[T | None]]:
    """
    Chunk an Async Iterator in to `n` sized chunks

    :param iterator: The iterator to chunk
    :param n: The size of the chunks
    """

    async def take(i, n) -> list[T | None]:
        return [item async for item in aslice(i, n)]

    if n < 1:
        raise ValueError("n must be at least one")

    it = aiter(aiterator)
    try:
        while chunk := await take(it, n):
            yield chunk
    except StopAsyncIteration:
        return


async def amerge(*aiterables: AsyncIterable[T | None]) -> AsyncIterator[T | None]:
    """
    Merge asynchronous iterables into a single stream

    :param *aiterables: The iterables to merge
    """
    iter_next: Dict[AsyncIterator[T | None], None | asyncio.Future] = {
        it.__aiter__(): None for it in aiterables
    }
    orig_iter: Dict[asyncio.Future, AsyncIterator[T | None]] = {}

    def supress_exception(fut: asyncio.Future):
        try:
            fut.result()
        except StopAsyncIteration:
            pass
        fut.remove_done_callback(supress_exception)

    while iter_next:
        for it, it_next in iter_next.items():
            if it_next is None:
                fut = asyncio.ensure_future(it.__anext__())
                fut.add_done_callback(supress_exception)

                orig_iter[fut] = it
                iter_next[it] = fut

        done, _ = await asyncio.wait(
            [fut for fut in iter_next.values() if fut], return_when=asyncio.ALL_COMPLETED
        )

        for fut in done:
            iter_next[orig_iter[fut]] = None
            try:
                ret = fut.result()
            except StopAsyncIteration:
                del iter_next[orig_iter[fut]]
                del orig_iter[fut]
                continue

            yield ret


async def timed_iter(
    aiterator: AsyncIterable[T | None], timeout: float, sentinel: None = None
) -> AsyncIterator[T | None]:
    """
    Wrap an async iterator into a timed iterator. If
    the iterator does not yield a value within `timeout`,
    then we yield a `sentinel`.

    :param aiterator: An asynchronous iterator to time
    :param timeout: The timeout to yield a sentinel
    :param sentinel: The sentinel value to yield after timeout
    """
    ait = aiter(aiterator)
    nxt = None
    try:
        nxt = asyncio.ensure_future(ait.__anext__())
        while True:
            try:
                yield await asyncio.wait_for(asyncio.shield(nxt), timeout)
                nxt = asyncio.ensure_future(ait.__anext__())
            except asyncio.TimeoutError:
                yield sentinel
    except StopAsyncIteration:
        pass
    finally:
        if nxt:
            nxt.cancel()  # in case we're getting cancelled our self


async def batch_streams(
    batch_size: int = 4, timeout: float = 1.0, *aiterables: AsyncIterable[T | None]
) -> AsyncIterator[list[T | None]]:
    """
    Merge and chunk a list of async iterables into `batch_size`

    :param batch_size: The size of the batches
    :param *aiterables: The asynchronous iterables to batch
    """
    aiterables = (*([timed_iter(iterable, timeout) for iterable in aiterables]),)
    async for batch in achunk(amerge(*aiterables), batch_size):
        yield batch


async def wait_for_value(
    condition: Callable,
    terminating_values: list | None = None,
    non_terminating_values: list | None = None,
    timeout: int = 10,
):
    """
    Asynchronously wait for a condition to reach a target value within a specified timeout.

    :param condition: The condition to check the value of. Must be a callable.
    :type condition: Any
    :param target_value: The target value that the variable should be.
    :type target_value: Any
    :param timeout: The maximum amount of time to wait in seconds.
    :type timeout: float

    :return: True if the variable is the target value, False if the timeout is reached before the
    variable is the target value.
    :rtype: bool
    """
    start_time = asyncio.get_running_loop().time()
    if terminating_values:
        full_condition = lambda: condition() not in (terminating_values or [])
    else:
        full_condition = lambda: condition() in (non_terminating_values or [])

    while value := full_condition():
        await asyncio.sleep(0.1)
        elapsed_time = asyncio.get_running_loop().time() - start_time
        if elapsed_time >= timeout:
            raise asyncio.TimeoutError
    return value


async def call_bash_command(
    command: list,
    stream_callbacks: list[Callable[..., None]] | None = None,
) -> tuple[int, str]:
    async def _read_stream(stream, callbacks):
        while True:
            line = (await stream.readline()).decode()

            if line:
                for callback in callbacks:
                    if callback:
                        if is_async_callable(callback):
                            await callback(line)
                        else:
                            callback(line)
            else:
                break

    process = await asyncio.create_subprocess_exec(
        command[0], *command[1:], stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    await asyncio.gather(
        _read_stream(process.stdout, [stdout_lines.append] + (stream_callbacks or [])),
        _read_stream(process.stderr, [stderr_lines.append] + (stream_callbacks or [])),
    )
    await process.wait()

    stdout = "\n".join(stdout_lines)
    stderr = "\n".join(stderr_lines)

    if process.returncode and process.returncode != 0:
        raise subprocess.CalledProcessError(
            process.returncode, command, output=stdout, stderr=stderr
        )

    return process.returncode or 0, stdout


def compute_exponential_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
) -> float:
    """
    Compute the exponential backoff delay

    :param attempt: The attempt number
    :type attempt: int
    :param base_delay: The base delay
    :type base_delay: float
    :param max_delay: The maximum delay
    :type max_delay: float
    :return: The exponential backoff delay
    :rtype: float
    """
    return min(base_delay * (2 ** attempt), max_delay)


async def retry(
    func: Callable[..., Awaitable[R]],
    should_retry: Callable[[Exception], bool],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
) -> R:
    """
    Retry a function until it succeeds

    :param func: The function to retry
    :type func: Callable
    :param should_retry: The function to determine if the function should be retried
    :type should_retry: Callable
    :param max_retries: The maximum number of retries
    :type max_retries: int
    :param base_delay: The base delay
    :type base_delay: float
    :param max_delay: The maximum delay
    :type max_delay: float
    :raises Exception: The exception
    :return: The result of the function
    :rtype: Any
    """
    max_retries = max(max_retries, 0)
    retries = 0

    while retries < max_retries:
        try:
            return await func()
        except Exception as e:
            if retries == max_retries - 1 or not should_retry(e):
                raise

            retries += 1
            await asyncio.sleep(compute_exponential_backoff(retries, base_delay, max_delay))

    raise RuntimeError("max retries exceeded")
