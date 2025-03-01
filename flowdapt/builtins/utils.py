import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Tuple, Union
from urllib.parse import quote

import dask.dataframe as dd
import numpy as np
import pandas as pd
import psutil

from flowdapt.lib.logger import get_logger
from flowdapt.lib.utils.misc import dict_to_list_string


logger = get_logger(__name__)


def find_labels(dataframe: pd.DataFrame) -> list:
    column_names = dataframe.columns
    labels = [c for c in column_names if c.startswith("&")]
    return labels


def find_features(dataframe: pd.DataFrame) -> list:
    column_names = dataframe.columns
    features = [c for c in column_names if c.startswith("%")]
    return features


def dummy_pandas_df(rows: int, cols: int, withnans: bool = True) -> pd.DataFrame:
    df = pd.DataFrame(np.random.rand(rows, cols)) * 35

    # fake features
    df.columns = [f"%-{col}" for col in df.columns]

    # fake label
    df = df.set_axis([*df.columns[:-1], "&-a"], axis=1)

    # fake nans
    if withnans:
        df = df.mask(df < 0.01)

    return df


def save_historical_data_to_feather(
    data: pd.DataFrame, metadata: Dict[str, Any], save_path: str
) -> bool:
    """
    Save the provided dataframe to feather in user_data/
    """
    md_list, md_str = dict_to_list_string(metadata)

    Path(save_path, *md_list).mkdir(parents=True, exist_ok=True)
    data_path = Path(save_path, *md_list) / f"{md_str}.feather"

    data.to_feather(data_path)

    return data_path.is_file()


def load_historical_data_from_feather(
    metadata: Dict[str, Any],
    save_path: str,
    num_points: int = -1,
) -> Union[pd.DataFrame, None]:
    """
    Given metadata, look for saved feather file and load it to dataframe
    if available. Else, log exception and return None
    """

    md_list, md_str = dict_to_list_string(metadata)

    try:
        df = pd.read_feather(Path(save_path, *md_list) / f"{md_str}.feather")
        if num_points < 0:
            return df
        else:
            # return only the latest num_points
            return df.tail(num_points)
    except Exception as e:
        logger.warning(f"Unable to load feather from {Path(save_path, *md_list)}. {e}")
        return None


def update_historic_data(
    metadata: Dict[str, Any], incoming_df: pd.DataFrame, save_path: str
) -> Tuple[bool, int]:
    """
    Append datapoint to the existing historic data. The incoming dataframe
    must have at least 1 candle.
    Date columns must be labeled 'date'
    """

    if incoming_df.empty:
        # The incoming dataframe must have at least 1 candle
        return (False, 0)

    existing_df = load_historical_data_from_feather(metadata, save_path, -1)

    if existing_df is None:
        return (False, 0)

    local_last = existing_df.iloc[-1]["date"]
    incoming_first = incoming_df.iloc[0]["date"]

    tf_delta = get_data_frequency(existing_df)

    existing_df1 = existing_df[existing_df["date"] < incoming_first]

    candle_difference = (incoming_first - local_last) / tf_delta

    if candle_difference > 1:
        logger.warning("Gap in data, should redownload from scratch.")

    existing_df = pd.concat([existing_df1, incoming_df], ignore_index=True)

    saved = save_historical_data_to_feather(existing_df, metadata, save_path)
    if not saved:
        logger.warning("Unable to save dataframe to feather at ", f"{save_path}, {metadata}")

    return (True, candle_difference)


def get_data_frequency(df: pd.DataFrame) -> timedelta:
    """
    Given a dataframe, checks the time between last two data points
    and considers this the data collection frequency.
    :param df: dataframe to be checked for data_frequency
    :return:
    timedelta in seconds
    """
    tf_delta = pd.to_timedelta(df["date"].iloc[-1] - df["date"].iloc[-2])

    return tf_delta


def path_from_string(s: str) -> Path:
    """
    Given a string, generate a path assuming the delimiters
    are "_"
    :param s: string to be converted to Path
    """

    # FIXME: will this work on windows?
    return Path(s.replace("_", "/"))


def merge_dataframes(
    df: pd.DataFrame, df_inc: pd.DataFrame, prefer_new: bool = True
) -> pd.DataFrame:
    if len(df_inc.index) == 0:
        # The incoming dataframe must have at least 1 candle
        return (False, 0)

    local_last = df["date"].iloc[-1]
    incoming_first = df_inc["date"].iloc[0]

    tf_delta = get_data_frequency(df)

    if prefer_new:
        df1 = df[df["date"] < incoming_first]
    else:
        df1 = df
        df_inc = df_inc[df_inc["date"] > local_last]

    candle_difference = (incoming_first - local_last) / tf_delta

    if candle_difference > 1:
        logger.warning("Gap in data, should redownload from scratch.")

    return pd.concat([df1, df_inc], ignore_index=True)


def get_data_gap(df: Union[pd.DataFrame, dd.DataFrame], tz: timezone | None = None) -> int:
    local_last = df.iloc[-1]["date"].tz_localize(tz)
    current_date = datetime.now(tz=tz)

    tf_delta = get_data_frequency(df)

    row_difference = (current_date - local_last) / tf_delta

    if int(row_difference) > 0:
        logger.info(f"Gap in data, downloading {int(row_difference)} points.")
        logger.info(
            f"Last data point: {local_last}, current time: {current_date} "
            f"tf_delta: {tf_delta}, row_difference: {row_difference}"
        )
    else:
        logger.info("No gap in data, pulling from memory/storage.")

    return int(row_difference)


def extract_features_and_labels(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extract features and labels assuming feature columns
    are prepended with "%" and label columns are
    prepended with "&"
    """
    labels = df.filter(find_labels(df))
    features = df.filter(find_features(df))

    if labels.empty:
        logger.error("No labels found")
    if features.empty:
        logger.error("No features found")

    return features, labels


def remove_rows_with_nans(df: pd.DataFrame) -> pd.DataFrame:
    drop_rows = pd.isnull(df).any(axis=1)
    df = df[~drop_rows]
    if len(df) < len(drop_rows):
        logger.warning(f"Dropped {len(drop_rows) - len(df.index)} from dataset due to NaNs")

    return df


def remove_none_columns(df: pd.DataFrame, threshold: int = 40) -> pd.DataFrame:
    """
    Remove columns that are entirely None and
    Remove columns that have More NaNs than threshold
    """

    incoming_cols = len(df.columns)
    total_num = len(df.index)
    df = df.dropna(axis=1, thresh=total_num - threshold)
    df = df.dropna(axis=1, how="all")
    outgoing_cols = len(df.columns)
    logger.info(f"Removed {incoming_cols - outgoing_cols} columns due to NaNs")
    return df


def shift_and_add_features(df: pd.DataFrame, shifts: int, cols: list) -> pd.DataFrame:
    """
    Automatically shifts entire dataframe `shifts` times and adds points
    to
    """
    for shift in range(shifts):
        if shift == 0:
            continue
        df_shift = df[cols].shift(shift)
        df_shift = df_shift.add_suffix(f"_shift-{shift}")
        df = pd.concat((df, df_shift), axis=1)

    return df


def get_current_threads_all_procs():
    total_threads = 0
    current_process = psutil.Process()
    total_threads += current_process.num_threads()

    for child in current_process.children(recursive=True):
        total_threads += child.num_threads()

    return total_threads


def get_total_system_threads():
    # get the list of all running processes
    processes = psutil.process_iter()

    # initialize the total number of threads
    total_threads = 0

    # iterate over all running processes and sum their number of threads
    for proc in processes:
        try:
            # get the number of threads for the current process
            num_threads = proc.num_threads()
            # add the number of threads to the total count
            total_threads += num_threads
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # handle exceptions that may occur during the process retrieval
            pass

    logger.info(f"Total number of processes in the system: {len(psutil.pids())}")
    logger.info(f"Total number of threads consumed by processes in the system: {total_threads}")

    with open("user_data/total_threads.txt", "a") as f:
        f.write(str(total_threads) + "\n")


def artifact_name_from_dict(d: dict) -> str:
    """
    Given a dictionary, create a valid artifact name
    :param d: base dict
    """

    l, s = dict_to_list_string(d)
    s = quote(s)
    # Remove any characters that are not allowed in file names using regex
    s = re.sub(r'[\\/:*?"<>|]', "", s)

    # Replace any spaces or special characters with an underscore or hyphen using regex
    s = re.sub(r"\s+", "-", s)
    s = s.replace("%", "")
    s = s.replace(" ", "_")
    s = s.replace(".", "_")
    return f"{s}"


def string_to_uuid(s):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, s))
