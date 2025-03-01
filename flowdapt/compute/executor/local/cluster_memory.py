# server.py
import asyncio
import os
from collections import defaultdict
from contextlib import suppress
from typing import Any, Type

from flowdapt.compute.cluster_memory.base import ClusterMemory
from flowdapt.lib.serializers import CloudPickleSerializer, Serializer
from flowdapt.lib.utils.asynctools import run_in_thread, syncify
from flowdapt.lib.utils.taskset import TaskSet


SOCKET_PATH = "/tmp/flowdapt-cluster-memory.sock"
LENGTH_BYTE_SIZE = 4
MAX_QUEUE_SIZE = 1000

CLOSE_CONNECTION_BYTES = b"CLOSE"

CONTROL_PACKETS = {
    CLOSE_CONNECTION_BYTES,
}


class Request:
    def __init__(self, operation: str, args: list):
        self.operation = operation
        self.args = args


class Response:
    def __init__(self, result: object, error: Exception | None = None):
        self.result = result
        self.exc = error


class CommunicationMixin:
    async def send_message(self, writer: asyncio.StreamWriter, message: bytes) -> None:
        message_length = len(message).to_bytes(LENGTH_BYTE_SIZE, "big")
        writer.write(message_length + message)
        await writer.drain()

    async def receive_message(self, reader: asyncio.StreamReader) -> bytes:
        # Read the first `n` bytes to get the length of the request
        # then read that many bytes. This is to avoid having to
        # append a delimiter to the end of the request since we
        # send pickled objects. Using 4 bytes for the length means
        # a single request can be up to 4GB in size.
        try:
            message_length_bytes = await reader.readexactly(LENGTH_BYTE_SIZE)
        except asyncio.IncompleteReadError:
            # If we can't read the message length, then the connection was closed.
            return CLOSE_CONNECTION_BYTES

        message_length = int.from_bytes(message_length_bytes, "big")
        message = await reader.readexactly(message_length)
        return message

    async def send_close(self, writer: asyncio.StreamWriter) -> None:
        await self.send_message(writer, CLOSE_CONNECTION_BYTES)

        writer.close()
        await writer.wait_closed()


class ClusterMemoryServer(CommunicationMixin):
    def __init__(
        self,
        path: str,
        serializer: Type[Serializer] = CloudPickleSerializer,
    ) -> None:
        self._path = path
        self._serializer = serializer
        self._store: dict[str, dict] = defaultdict(dict)
        self._server: asyncio.AbstractServer | None = None
        self._tasks = TaskSet()

    async def start(self):
        if os.path.exists(self._path):
            os.remove(self._path)

        self._server = await asyncio.start_unix_server(self._create_connection, self._path)
        await self._server.start_serving()

    async def close(self):
        self._store = {}

        if os.path.exists(self._path):
            os.remove(self._path)

        if self._server:
            self._server.close()

            self._tasks.cancel()
            with suppress(asyncio.CancelledError):
                await self._tasks

            await self._server.wait_closed()

    async def _create_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self._tasks.add(self._handle_client(reader, writer))

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            while True:
                request_bytes = await self.receive_message(reader)

                # Close the connection if we receive an empty request
                if request_bytes == CLOSE_CONNECTION_BYTES:
                    break

                response = await run_in_thread(self._process_request, request_bytes)
                await self.send_message(writer, response)
        except ConnectionResetError:
            pass
        finally:
            writer.close()

    def _process_request(self, request_bytes: bytes):
        try:
            # Deserialize the request and process it
            request = CloudPickleSerializer.loads(request_bytes)
            op_return = self._perform_operation(request)

            # If the operation returns a value, serialize it and return it
            response = Response(op_return)
        except Exception as e:
            # If there was an error, send it to the client
            response = Response(None, e)

        return CloudPickleSerializer.dumps(response)

    def _perform_operation(self, request: Request):
        match request.operation:
            case "get":
                return self._handle_get(*request.args)
            case "put":
                return self._handle_put(*request.args)
            case "delete":
                return self._handle_delete(*request.args)
            case "clear":
                return self._handle_clear()
            case _:
                raise ValueError(f"Invalid operation: {request.operation}")

    def _handle_get(self, key: str, namespace: str = "default"):
        return self._store[namespace][key]

    def _handle_put(self, key: str, value: Any, namespace: str = "default"):
        self._store[namespace][key] = value
        return "OK"

    def _handle_delete(self, key: str, namespace: str = "default"):
        if namespace in self._store and key in self._store[namespace]:
            del self._store[namespace][key]

            if not self._store[namespace]:
                del self._store[namespace]

            return "OK"

    def _handle_clear(self):
        self._store = {}
        return "OK"


class ClusterMemoryClient(CommunicationMixin):
    def __init__(
        self,
        path: str,
        serializer: Type[Serializer] = CloudPickleSerializer,
    ):
        self._path = path
        self._serializer = serializer

    @syncify
    async def put(self, key: str, value: Any, *, namespace: str = "default"):
        return await self.send_request({"operation": "put", "args": [key, value, namespace]})

    @syncify
    async def get(self, key: str, *, namespace: str = "default"):
        return await self.send_request({"operation": "get", "args": [key, namespace]})

    @syncify
    async def delete(self, key: str, *, namespace: str = "default"):
        return await self.send_request({"operation": "delete", "args": [key, namespace]})

    @syncify
    async def clear(self):
        return await self.send_request({"operation": "clear", "args": []})

    async def send_request(self, request: dict):
        # TODO: Avoid creating connection for every request, and instead use
        # the same connection the entire time of the stage. This will require
        # some machinery to handle closing the connection without the user explicitly
        # having to do it.
        reader, writer = await asyncio.open_unix_connection(self._path)

        request_obj = Request(**request)
        serialized_request = self._serializer.dumps(request_obj)
        await self.send_message(writer, serialized_request)

        serialized_response = await self.receive_message(reader)
        response = self._serializer.loads(serialized_response)

        if response.exc:
            # If the server returned an exception, raise it here
            raise response.exc

        await self.send_close(writer)
        return response.result


class LocalClusterMemory(ClusterMemory):
    def __init__(self):
        self._client = ClusterMemoryClient(SOCKET_PATH)

    def get(self, key: str, *, namespace: str = "default"):
        return self._client.get(key, namespace=namespace)

    def put(self, key: str, value: Any, *, namespace: str = "default"):
        return self._client.put(key, value, namespace=namespace)

    def delete(self, key: str, *, namespace: str = "default"):
        return self._client.delete(key, namespace=namespace)

    def clear(self):
        return self._client.clear()
