import pytest
from unittest.mock import MagicMock

from flowdapt.compute.artifacts import (
    _get_values_from_context,
    new_artifact,
    list_artifacts,
    get_artifact
)


@pytest.fixture(scope="function")
def mocked_default_values(mocker):
    mock_default_values = mocker.patch("flowdapt.compute.artifacts._get_values_from_context")
    mock_default_values.return_value = ("default", "memory", "", {})

    return mock_default_values

@pytest.fixture(scope="function")
def mocked_artifact(mocker):
    mock_artifact = mocker.patch("flowdapt.compute.artifacts.Artifact")
    mock_artifact.get_artifact.return_value = "mock_artifact"
    mock_artifact.new_artifact.return_value = "new_mock_artifact"
    mock_artifact.list_artifacts.return_value = ["mock_artifact1", "mock_artifact2"]

    return mock_artifact


def test_get_values_from_context(mocker):
    # Create a mock context with the desired structure
    mock_context = MagicMock()
    mock_context.namespace = "default"
    mock_config = MagicMock()
    mock_config.storage.protocol = "memory"
    mock_config.storage.base_path = "test"
    mock_config.storage.parameters = {"param1": "value1"}

    # Make get_run_context return the mock context
    mocker.patch("flowdapt.compute.artifacts.get_run_context", return_value=mock_context)
    mocker.patch("flowdapt.compute.artifacts.get_configuration", return_value=mock_config)

    # Call _default_values with some arguments
    namespace, protocol, base_path, params = _get_values_from_context(
        namespace="",
        protocol="",
        base_path="",
        param2="value2"
    )

    # Check that the returned values are what we expect
    assert namespace == "default"
    assert protocol == "memory"
    assert base_path == "test"
    assert params == {"param1": "value1", "param2": "value2"}


def test_get_artifact(mocked_default_values, mocked_artifact):
    artifact = get_artifact("test_artifact")
    
    assert artifact == "mock_artifact"
    mocked_default_values.assert_called_once_with(namespace='', protocol='', base_path='')
    mocked_artifact.get_artifact.assert_called_once_with(
        name="test_artifact", 
        namespace="default", 
        protocol="memory", 
        base_path="", 
        **{}
    )


def test_list_artifacts(mocked_default_values, mocked_artifact):
    artifacts = list_artifacts()

    assert artifacts == ["mock_artifact1", "mock_artifact2"]
    mocked_default_values.assert_called_once_with(namespace='', protocol='', base_path='')
    mocked_artifact.list_artifacts.assert_called_once_with(
        namespace="default", 
        protocol="memory", 
        base_path="", 
        **{}
    )

def test_new_artifact(mocked_default_values, mocked_artifact):
    artifact = new_artifact("test_artifact")

    assert artifact == "new_mock_artifact"
    mocked_default_values.assert_called_once_with(namespace='', protocol='', base_path='')
    mocked_artifact.new_artifact.assert_called_once_with(
        name="test_artifact", 
        namespace="default", 
        protocol="memory", 
        base_path="", 
        **{}
    )

def test_get_artifact_with_create_true(mocked_default_values, mocked_artifact):
    mocked_artifact.get_artifact.side_effect = FileNotFoundError
    artifact = get_artifact("test_artifact", create=True)
    
    assert artifact == "new_mock_artifact"
    mocked_default_values.assert_called_once_with(namespace='', protocol='', base_path='')
    mocked_artifact.get_artifact.assert_called_once()
    mocked_artifact.new_artifact.assert_called_once_with(
        name="test_artifact", 
        namespace="default", 
        protocol="memory", 
        base_path="", 
        **{}
    )


def test_get_artifact_not_found(mocked_default_values, mocked_artifact):
    mocked_artifact.get_artifact.side_effect = FileNotFoundError

    with pytest.raises(FileNotFoundError):
        get_artifact("nonexistent_artifact")

    mocked_default_values.assert_called_once_with(namespace='', protocol='', base_path='')
    mocked_artifact.get_artifact.assert_called_once_with(
        name="nonexistent_artifact", 
        namespace="default", 
        protocol="memory", 
        base_path="", 
        **{}
    )


def test_list_artifacts_with_nondefault_values(mocked_default_values, mocked_artifact):
    mocked_default_values.return_value = ("custom_namespace", "file", "/custom/path", {"custom_param": "value"})

    artifacts = list_artifacts(namespace="custom_namespace", protocol="file", base_path="/custom/path", custom_param="value")

    assert artifacts == ["mock_artifact1", "mock_artifact2"]
    mocked_default_values.assert_called_once_with(namespace='custom_namespace', protocol='file', base_path='/custom/path', custom_param="value")
    mocked_artifact.list_artifacts.assert_called_once_with(
        namespace="custom_namespace", 
        protocol="file", 
        base_path="/custom/path", 
        custom_param="value"
    )


def test_new_artifact_with_nondefault_values(mocked_default_values, mocked_artifact):
    mocked_default_values.return_value = ("custom_namespace", "file", "/custom/path", {"custom_param": "value"})

    artifact = new_artifact("test_artifact", namespace="custom_namespace", protocol="file", base_path="/custom/path", custom_param="value")

    assert artifact == "new_mock_artifact"
    mocked_default_values.assert_called_once_with(namespace='custom_namespace', protocol='file', base_path='/custom/path', custom_param="value")
    mocked_artifact.new_artifact.assert_called_once_with(
        name="test_artifact", 
        namespace="custom_namespace", 
        protocol="file", 
        base_path="/custom/path", 
        custom_param="value"
    )