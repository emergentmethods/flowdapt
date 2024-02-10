from abc import ABC, abstractmethod
from typing import Any


class ClusterMemory(ABC):
    """
    Abstract class for Executor specific cluster memory.
    """

    @abstractmethod
    def get(self, key: str, *, namespace: str = "default") -> Any:
        """
        Get a value from the cluster memory.

        :param key: Key to get the value for.
        :return: Value for the key.
        """
        pass

    @abstractmethod
    def put(self, key, value, *, namespace: str = "default") -> None:
        """
        Put a value in the cluster memory.

        :param key: Key to set the value for.
        :param value: Value to set.
        """
        pass

    @abstractmethod
    def delete(self, key: str, *, namespace: str = "default"):
        """Delete a value from the cluster memory.

        :param key: Key to delete the value for.
        :type key: str
        :param namespace: Namespace to delete the value from, defaults to default.
        """
        pass

    @abstractmethod
    def clear(self):
        """
        Clear the cluster memory.
        """
        pass
