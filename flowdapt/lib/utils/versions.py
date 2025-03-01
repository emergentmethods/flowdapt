from typing import Any

from packaging.version import Version as PyPIVersion
from semver import VersionInfo as Version

from flowdapt.lib.utils.model import IS_V1


if IS_V1:
    # Courtesy of:
    # https://python-semver.readthedocs.io/en/latest/advanced/combine-pydantic-and-semver.html
    class PydanticVersion(Version):
        @classmethod
        def _parse(cls, version):
            return cls.parse(version)

        @classmethod
        def __get_validators__(cls):
            """Return a list of validator methods for pydantic models."""
            yield cls._parse

        @classmethod
        def __modify_schema__(cls, field_schema: dict):
            """Inject/mutate the pydantic field schema in-place."""
            field_schema.update(
                examples=[
                    "1.0.2",
                    "2.15.3-alpha",
                    "21.3.15-beta+12345",
                ]
            )
else:
    from pydantic import (
        GetCoreSchemaHandler,
        GetJsonSchemaHandler,
    )
    from pydantic.json_schema import JsonSchemaValue  # type: ignore
    from pydantic_core import CoreSchema, core_schema

    class PydanticVersion(Version):
        @classmethod
        def _parse(cls, version, _):
            return cls.parse(version)

        @classmethod
        def __get_pydantic_json_schema__(
            cls,
            _core_schema: core_schema.JsonSchema,
            handler: GetJsonSchemaHandler,
        ) -> JsonSchemaValue:
            schema = handler(core_schema.str_schema())
            schema.update(
                examples=[
                    "1.0.2",
                    "2.15.3-alpha",
                    "21.3.15-beta+12345",
                ]
            )
            return schema

        @classmethod
        def __get_pydantic_core_schema__(
            cls,
            source_type: Any,
            handler: GetCoreSchemaHandler,
        ) -> CoreSchema:
            return core_schema.general_plain_validator_function(cls._parse)


def parse_version(version: str, optional_minor_and_patch: bool = False) -> Version:
    """
    Parse a version string into a semver version.
    """
    return Version.parse(version)


def parse_pypi_version(version: str) -> PyPIVersion:
    """
    Parse a version string into a PyPI version.
    """
    return PyPIVersion(version)


def satisfies_constraints(version: str | Version, constraints: str) -> bool:
    """
    Check if a version satisfies a set of constraints.

    Example:
        >>> satisfies_constraints("1.0.0", ">=1.0.0")
        True
        >>> satisfies_constraints("1.0.0", ">=1.0.0,<2.0.0")
        True
        >>> satisfies_constraints("1.0.0", ">=1.0.0,<1.0.0")
        False
    """
    if isinstance(version, str):
        version = parse_version(version)

    return all(version.match(c) for c in constraints.split(","))


def compare_versions(
    left: str | Version, right: str | Version, optional_minor_and_patch: bool = False
) -> int:
    """
    Compare two versions.

    Example:
        >>> compare_versions("1.0.0", "1.0.1")
        -1
        >>> compare_versions("1.0.0", "1.0.0")
        0
        >>> compare_versions("1.0.1", "1.0.0")
        1
    """
    if isinstance(left, str):
        left = parse_version(left, optional_minor_and_patch=optional_minor_and_patch)

    if isinstance(right, str):
        right = parse_version(right, optional_minor_and_patch=optional_minor_and_patch)

    return left.compare(right)


def pypi2semver(version: PyPIVersion) -> Version:
    """
    Converts a PyPI version into a semver version

    :param ver: the PyPI version
    :return: a semver version
    """
    pre = None if not version.pre else "".join([str(i) for i in version.pre])
    major, minor, patch = version.release
    return Version(major=major, minor=minor, patch=patch, prerelease=pre, build=version.dev)


def semver2pypi(version: Version) -> PyPIVersion:
    """
    Converts a semver version into a version from PyPI

    A semver prerelease will be converted into a
    prerelease of PyPI.
    A semver build will be converted into a development
    part of PyPI
    :param semver.Version ver: the semver version
    :return: a PyPI version
    """
    v = version.finalize_version()
    prerelease = version.prerelease if version.prerelease else ""
    build = version.build if version.build else ""
    return PyPIVersion(f"{v}{prerelease}{build}")
