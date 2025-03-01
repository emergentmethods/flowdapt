import base64
import pickle
import secrets
from typing import Any

import cloudpickle
import dill
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from flowdapt.lib.serializers.base import Serializer


class PickleSerializer(Serializer):
    """
    An serializer that uses the builtin
    pickle module to serialize and deserialize objects.
    """

    @staticmethod
    def dumps(value: Any) -> bytes:
        return pickle.dumps(value)

    @staticmethod
    def loads(value: bytes) -> Any:
        return pickle.loads(value)


class CloudPickleSerializer(Serializer):
    """
    A serializer that uses the cloudpickle library
    to serialize and deserialize objects.
    """

    @staticmethod
    def dumps(value: Any) -> bytes:
        return cloudpickle.dumps(value)

    @staticmethod
    def loads(value: bytes) -> Any:
        return cloudpickle.loads(value)


class DillPickleSerializer(Serializer):
    """
    A serializer that uses the dill library
    to serialize and deserialize objects.
    """

    @staticmethod
    def dumps(value: Any) -> bytes:
        return dill.dumps(value)

    @staticmethod
    def loads(value: bytes) -> Any:
        return dill.loads(value)


class SecureCloudPickleSerializer(Serializer):
    salt_size = 16

    def __init__(self, key: str):
        self._key = key

    def _fernet_from_key(self, salt: bytes):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        return Fernet(base64.urlsafe_b64encode(kdf.derive(self._key.encode())))

    def _get_salt(self):
        return secrets.token_bytes(self.salt_size)

    def dumps(self, value: Any) -> bytes:  # type: ignore
        salt = self._get_salt()
        fernet = self._fernet_from_key(salt)

        pickled_data = cloudpickle.dumps(value)
        encrypted_pickle = fernet.encrypt(pickled_data)

        return salt + encrypted_pickle

    def loads(self, value: bytes) -> Any:  # type: ignore
        salt = value[: self.salt_size]
        fernet = self._fernet_from_key(salt)

        encrypted_pickle = value[self.salt_size :]
        pickled_data = fernet.decrypt(encrypted_pickle)

        return cloudpickle.loads(pickled_data)
