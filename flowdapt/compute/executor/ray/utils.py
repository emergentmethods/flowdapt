import asyncio

from ray import ObjectRef


def objectref_to_future(object_ref: ObjectRef):
    """
    Converts a Ray ObjectRef to an Asyncio Future
    """
    return asyncio.wrap_future(object_ref.future())
