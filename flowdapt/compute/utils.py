import os

import psutil
import pynvml

from flowdapt.lib.logger import get_logger


logger = get_logger(__name__)


def get_available_cores():
    """
    Get the available cores for this machine using
    CPU affinity.
    """
    # https://stackoverflow.com/a/55423170
    # We want to use affinity because some cluster solutions
    # can limit CPU's. psutil offers a solution that works on
    # Unix and Windows
    return len(psutil.Process().cpu_affinity()) - 1


def get_available_gpus():
    pynvml.nvmlInit()
    return pynvml.nvmlDeviceGetCount()


def get_total_memory():
    """
    Get the total RAM installed on this machine in bytes.
    """
    memory_info = psutil.virtual_memory()
    return memory_info.total


def parse_cuda_visible_device(dev):
    """
    Parses a single CUDA device identifier
    A device identifier must either be an integer, a string containing an
    integer or a string containing the device's UUID, beginning with prefix
    'GPU-' or 'MIG-'.
    >>> parse_cuda_visible_device(2)
    2
    >>> parse_cuda_visible_device('2')
    2
    >>> parse_cuda_visible_device('GPU-9baca7f5-0f2f-01ac-6b05-8da14d6e9005')
    'GPU-9baca7f5-0f2f-01ac-6b05-8da14d6e9005'
    >>> parse_cuda_visible_device('Foo')
    Traceback (most recent call last):
    ...
    ValueError: Devices in CUDA_VISIBLE_DEVICES must be comma-separated integers or
    strings beginning with 'GPU-' or 'MIG-' prefixes.
    """
    try:
        return int(dev)
    except ValueError:
        if any(
            dev.startswith(prefix)
            for prefix in [
                "GPU-",
                "MIG-",
            ]
        ):
            return dev
        else:
            raise ValueError(
                "Devices in CUDA_VISIBLE_DEVICES must be comma-separated integers "
                "or strings beginning with 'GPU-' or 'MIG-' prefixes."
            )


def cuda_visible_devices(i, visible=None):
    """Cycling values for CUDA_VISIBLE_DEVICES environment variable
    Examples
    --------
    >>> cuda_visible_devices(0, range(4))
    '0,1,2,3'
    >>> cuda_visible_devices(3, range(8))
    '3,4,5,6,7,0,1,2'
    """
    if visible is None:
        try:
            visible = map(parse_cuda_visible_device, os.environ["CUDA_VISIBLE_DEVICES"].split(","))
        except KeyError:
            visible = range(get_available_gpus())
    visible = list(visible)

    L = visible[i:] + visible[:i]
    return L  # ",".join(map(str, L))


def parse_gpu_input(gpus):
    """
    Given the config input of `gpus`, parse it from
    auto, integer, list of integers, or string,
    """
    if gpus == "auto":
        gpus = cuda_visible_devices(0)
    elif isinstance(gpus, int):
        gpus = list(range(gpus))
    # Is "disabled" what we want here?
    elif isinstance(gpus, str) and gpus.lower() == "disabled":
        gpus = []
    elif isinstance(gpus, str):
        gpus = gpus.split(",")
    else:
        gpus = []

    # Store list of GPU devices and set of available GPUs
    found_gpus = list(map(parse_cuda_visible_device, gpus))

    if found_gpus:
        assert len(found_gpus) == get_available_gpus(), "Invalid GPU devices provided"
        logger.info(f"Using available GPUs: {found_gpus}")

    return found_gpus
