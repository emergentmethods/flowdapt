import asyncio

from ray import ObjectRef


async def objectref_to_future(object_ref: ObjectRef) -> asyncio.Future:
    """
    Converts a Ray ObjectRef to an Asyncio Future
    """
    # In Ray Client mode, object_ref.future() blocks the calling thread waiting
    # for the server to ACK task submission and assign an ID (_wait_for_id).
    # Running it in a thread prevents stalling the event loop under server load.
    concurrent_future = await asyncio.to_thread(object_ref.future)
    return asyncio.wrap_future(concurrent_future)
