import pytest

from flowdapt.compute.artifacts import Artifact


@pytest.fixture(scope="function")
def artifact_params():
    return {"protocol": "memory", "base_path": "test"}

@pytest.fixture(scope="function")
def artifact(artifact_params):
    artifact = Artifact.new_artifact(
        name="test_artifact",
        **artifact_params
    )
    try:
        yield artifact
    finally:
        artifact.delete()


@pytest.mark.parametrize(
    "artifact_name,expected_uri",
    [
        ("test_artifact", "memory://test/artifacts/default/test_artifact")
    ]
)
def test_artifact_creation(artifact_params, artifact_name, expected_uri):
    artifact = Artifact.new_artifact(artifact_name, **artifact_params)
    try:
        assert artifact.uri == expected_uri
        assert artifact.is_empty == True
        assert artifact.exists == True
    finally:
        # Clean up
        artifact.delete()


def test_artifact_delete(artifact_params):
    artifact = Artifact.new_artifact("test_artifact", **artifact_params)
    artifact.delete()

    # Make sure the artifact is marked as deleted
    assert artifact.is_empty == True
    assert artifact.exists == False

    # Make sure further operations raise an error
    with pytest.raises(FileNotFoundError):
        artifact.get_file("test_file")

    with pytest.raises(FileNotFoundError):
        artifact.list_files()

    with pytest.raises(FileNotFoundError):
        artifact.new_file("test_file", "test_content")


@pytest.mark.parametrize(
    "file_name,content,expected_content",
    [
        ("test_file", "test_content", b"test_content"),
        ("empty_file", None, b""),
    ]
)
def test_artifact_file_creation_and_reading(artifact: Artifact, file_name, content, expected_content):
    file = artifact.new_file(file_name, content)

    assert file.name == file_name
    assert file.read() == expected_content
    assert not artifact.is_empty


def test_metadata(artifact: Artifact):
    artifact["key1"] = "value1"
    artifact["key2"] = 10
    artifact.set_meta("key3", [1, 2, 3])

    assert artifact["key1"] == "value1"
    assert artifact.metadata["key2"] == 10
    assert artifact.get_meta("key3") == [1, 2, 3]


def test_artifact_file_deletion(artifact: Artifact):
    file_name = "test_file"

    artifact.new_file(file_name, "test_content")
    artifact.delete_file(file_name)

    with pytest.raises(FileNotFoundError):
        artifact.get_file(file_name)

    assert artifact.exists
    assert artifact.is_empty
    assert artifact.list_files() == []


def test_duplicate_file_creation(artifact: Artifact):
    file_name = "test_file"
    artifact.new_file(file_name, "test_content")

    with pytest.raises(FileExistsError):
        artifact.new_file(file_name, "test_content", exist_ok=False)

    artifact.new_file(file_name, "test_content", exist_ok=True)


def test_nonexistent_file_deletion(artifact: Artifact):
    file_name = "nonexistent_file"
    with pytest.raises(FileNotFoundError):
        artifact.delete_file(file_name)


def test_invalid_parameters(artifact_params):
    with pytest.raises(AssertionError):
        artifact = Artifact.new_artifact("", **artifact_params)

    artifact = Artifact.new_artifact("test_artifact", **artifact_params)

    with pytest.raises(TypeError):
        artifact.new_file("test_file", {"test": "dict"})

    artifact.delete()


def test_artifact_clear(artifact: Artifact):
    file_name = "test_file"
    artifact.new_file(file_name, "test_content")

    artifact.clear()

    assert artifact.list_files() == []