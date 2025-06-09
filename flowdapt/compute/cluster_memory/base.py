from abc import ABC, abstractmethod
from typing import Any, List

from asyncer import syncify


class ClusterMemory(ABC):
    """
    Abstract class for Executor specific cluster memory.
    """
    @abstractmethod
    async def aget(self, key: str, *, namespace: str = "default") -> Any:
        """
        Get a value from the cluster memory.

        :param key: Key to get the value for.
        :type key: str
        :param namespace: Namespace to get the value from, defaults to default.
        :type namespace: str
        :return: Value for the key.
        :rtype: Any
        """
        pass

    @abstractmethod
    async def aput(self, key: str, value: Any, *, namespace: str = "default") -> None:
        """
        Put a value in the cluster memory.

        :param key: Key to set the value for.
        :type key: str
        :param value: Value to set.
        :type value: Any
        :param namespace: Namespace to put the value in, defaults to default.
        :type namespace: str
        :return: None
        :rtype: None
        """
        pass

    @abstractmethod
    async def adelete(self, key: str, *, namespace: str = "default") -> None:
        """Delete a value from the cluster memory.

        :param key: Key to delete the value for.
        :type key: str
        :param namespace: Namespace to delete the value from, defaults to default.
        :type namespace: str
        :return: None
        :rtype: None
        """
        pass

    @abstractmethod
    async def alist(self, prefix: str | None = None, *, namespace: str = "default") -> List[str]:
        """
        List all keys in the cluster memory for a given namespace.

        :param prefix: Optional prefix to filter keys.
        :type prefix: str | None
        :param namespace: Namespace to list keys from.
        :type namespace: str
        :return: List of keys in the cluster memory.
        :rtype: List[str]
        """
        pass

    @abstractmethod
    async def aexists(self, key: str, *, namespace: str = "default") -> bool:
        """
        Check if a key exists in the cluster memory.

        :param key: Key to check for existence.
        :type key: str
        :param namespace: Namespace to check in, defaults to default.
        :type namespace: str
        :return: True if the key exists, False otherwise.
        :rtype: bool
        """
        pass

    @abstractmethod
    async def aclear(self, *, namespace: str | None = None) -> None:
        """
        Clear the cluster memory.

        :param namespace: Namespace to clear, defaults to None which clears all namespaces.
        :type namespace: str | None
        :return: None
        :rtype: None
        """
        pass

    def get(self, key: str, *, namespace: str = "default") -> Any:
        """
        Get a value from the cluster memory.

        :param key: Key to get the value for.
        :type key: str
        :param namespace: Namespace to get the value from, defaults to default.
        :type namespace: str
        :return: Value for the key.
        :rtype: Any
        """
        return syncify(self.aget, raise_sync_error=False)(key, namespace=namespace)

    def put(self, key: str, value: Any, *, namespace: str = "default") -> None:
        """
        Put a value in the cluster memory.

        :param key: Key to set the value for.
        :type key: str
        :param value: Value to set.
        :type value: Any
        :param namespace: Namespace to put the value in, defaults to default.
        :type namespace: str
        :return: None
        :rtype: None
        """
        return syncify(self.aput, raise_sync_error=False)(key, value, namespace=namespace)

    def delete(self, key: str, *, namespace: str = "default") -> None:
        """
        Delete a value from the cluster memory.

        :param key: Key to delete the value for.
        :type key: str
        :param namespace: Namespace to delete the value from, defaults to default.
        :type namespace: str
        :return: None
        :rtype: None
        """
        return syncify(self.adelete, raise_sync_error=False)(key, namespace=namespace)

    def list(self, prefix: str | None = None, *, namespace: str = "default") -> List[str]:
        """
        List all keys in the cluster memory for a given namespace.

        :param prefix: Optional prefix to filter keys.
        :type prefix: str | None
        :param namespace: Namespace to list keys from.
        :type namespace: str
        :return: List of keys in the cluster memory.
        :rtype: List[str]
        """
        return syncify(self.alist, raise_sync_error=False)(prefix, namespace=namespace)

    def exists(self, key: str, *, namespace: str = "default") -> bool:
        """
        Check if a key exists in the cluster memory.

        :param key: Key to check for existence.
        :type key: str
        :param namespace: Namespace to check in, defaults to default.
        :type namespace: str
        :return: True if the key exists, False otherwise.
        :rtype: bool
        """
        return syncify(self.aexists, raise_sync_error=False)(key, namespace=namespace)

    def clear(self, *, namespace: str | None = None) -> None:
        """
        Clear the cluster memory.

        :param namespace: Namespace to clear, defaults to None which clears all namespaces.
        :type namespace: str | None
        :return: None
        :rtype: None
        """
        return syncify(self.aclear, raise_sync_error=False)(namespace=namespace)
