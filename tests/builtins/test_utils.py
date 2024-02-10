from flowdapt.builtins.utils import (
    remove_rows_with_nans,
    extract_features_and_labels,
)
from flowdapt.lib.logger import get_logger

logger = get_logger(__name__)


def test_remove_rows_with_nans(dummy_df_with_nans):

    df = dummy_df_with_nans
    assert len(df.index) == 100
    df = remove_rows_with_nans(df)
    assert len(df.index) == 96


def test_remove_rows_with_nans_when_no_nans(dummy_df_without_nans):
    df = dummy_df_without_nans
    assert len(df.index) == 100
    df = remove_rows_with_nans(df)
    assert len(df.index) == 100


def test_extract_features_and_labels(dummy_df_without_nans):
    features, labels = extract_features_and_labels(dummy_df_without_nans)
    assert len(features.columns) == 199
    assert len(labels) == 100


def test_extract_features_and_labels_without_label(dummy_df_without_nans, caplog):

    df = dummy_df_without_nans
    df = df.filter(like="%")
    features, labels = extract_features_and_labels(df)

    assert len(features.columns) == 199
    assert labels.empty


def test_extract_features_and_labels_without_feature(dummy_df_without_nans, caplog):

    df = dummy_df_without_nans
    df = df.filter(like="&")
    features, labels = extract_features_and_labels(df)

    assert features.empty
    assert len(labels) == 100
