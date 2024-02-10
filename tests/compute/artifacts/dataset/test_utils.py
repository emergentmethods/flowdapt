import pandas
import pytest

from flowdapt.compute.artifacts.dataset.utils import split_dataframe


@pytest.fixture
def sample_dataframe():
    return pandas.DataFrame({'A': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})


def test_split_dataframe_equal_chunks(sample_dataframe):
    chunks = split_dataframe(sample_dataframe, 2)
    assert len(chunks) == 2
    assert len(chunks[0]) == 5
    assert len(chunks[1]) == 5


def test_split_dataframe_unequal_chunks(sample_dataframe):
    chunks = split_dataframe(sample_dataframe, 3)
    assert len(chunks) == 3
    assert len(chunks[0]) == 4
    assert len(chunks[1]) == 3
    assert len(chunks[2]) == 3


def test_split_dataframe_single_chunk(sample_dataframe):
    chunks = split_dataframe(sample_dataframe, 1)
    assert len(chunks) == 1
    assert len(chunks[0]) == 10


def test_split_dataframe_zero_or_negative_chunks(sample_dataframe):
    with pytest.raises(ZeroDivisionError):
        split_dataframe(sample_dataframe, 0)

    with pytest.raises(ZeroDivisionError):
        split_dataframe(sample_dataframe, -2)
