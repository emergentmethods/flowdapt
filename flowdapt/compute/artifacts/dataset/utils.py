import pandas


def _get_current_executor():  # pragma: no cover
    # Get the current executor from the run context
    from flowdapt.compute.resources.workflow.context import get_run_context
    try:
        return get_run_context().executor
    except RuntimeError:
        return None


def split_dataframe(dataframe: pandas.DataFrame, n: int) -> list[pandas.DataFrame]:
    """
    Split a dataframe into `n` chunks.

    :param dataframe: The dataframe to split.
    :param n: The number of chunks to split the dataframe into.
    :return: A list of dataframes.
    """
    if n <= 0:
        raise ZeroDivisionError("Cannot split dataframe into zero or negative chunks.")

    num_rows = len(dataframe)
    chunk_size = num_rows // n
    remainder = num_rows % n

    # Uneven chunks will be distributed across the first few chunks
    return [
        dataframe.iloc[i * chunk_size + min(i, remainder):(i + 1) * chunk_size + min(i + 1, remainder)]  # noqa: E501
        for i in range(n)
    ]
