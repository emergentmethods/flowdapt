import logging
from copy import deepcopy

from distributed import SpecCluster

from flowdapt.compute.utils import parse_gpu_input
from flowdapt.lib.logger import get_logger


logger = get_logger(__name__)


class GPUCluster(SpecCluster):
    def __init__(self, gpus: str | list = "auto", *args, **kwargs) -> None:
        self.gpus = parse_gpu_input(gpus)

        # Required values
        kwargs.update(
            {
                # "shutdown_on_close": False,
                "silence_logs": logging.CRITICAL,
                "asynchronous": True,
            }
        )
        super().__init__(*args, **kwargs)

    def new_worker_spec(self, *args, **kwargs) -> dict:
        """Return a new worker specification for a worker on this cluster."""
        worker_id = self._get_worker_name()
        worker_spec = deepcopy(self.new_spec)

        options = worker_spec["options"]

        # Ensure worker specification contains environment and resources dictionaries
        if "env" not in options:
            options["env"] = {}

        if "resources" not in options:
            options["resources"] = {}

        # If GPU's are enabled, check if we can assign a GPU to the worker
        if self.gpus:
            gpu = self._get_next_gpu()
            if gpu is not None:
                logger.info("AssignedWorkerGPU", worker=worker_id, gpu=gpu)
                # Set the CUDA_VISIBLE_DEVICES environment variable for the worker
                options["env"]["CUDA_VISIBLE_DEVICES"] = str(gpu)
                # Set the "gpus" resource in the worker specification
                options["resources"]["gpus"] = 1
            else:
                logger.info("NoAvailableGPUs", worker=worker_id)
                # Explicitly remove the CUDA_VISIBLE_DEVICES environment variable
                # and "GPU" resource from the worker specification
                options["env"]["CUDA_VISIBLE_DEVICES"] = ""

        # Return the updated worker specification
        return {worker_id: worker_spec}

    def _get_worker_name(self):
        """
        Increment the worker ID until a unique name is found.
        """
        while self._i in self.worker_spec.keys():
            self._i += 1
        return self._i

    def _get_next_gpu(self):
        """Return the ID of the next available GPU."""
        for gpu in self.gpus:
            assigned = False
            for worker_spec in self.worker_spec.values():
                if worker_spec["options"]["env"].get("CUDA_VISIBLE_DEVICES") == str(gpu):
                    assigned = True
                    break
            if not assigned:
                return gpu
        return None
