from flowdapt.compute.domain.models.workflow import WorkflowResource
from flowdapt.compute.resources.workflow.stage import BaseStage
from flowdapt.compute.resources.workflow.utils import topological_sort_grouped
from flowdapt.lib.utils.misc import OrderedSet


class WorkflowGraph:
    """
    The WorkflowGraph creates a graph given a definition for
    iterating over stages in order.
    """

    def __init__(
        self,
        stages: list[BaseStage],
    ):
        self._graph: dict[str, OrderedSet[str]] = {}
        self._stages: dict[str, BaseStage] = {}

        self.add_stages(stages)

    def __repr__(self):
        return (
            f"WorkflowGraph("
            f"stages={', '.join([str(stage.__repr__()) for stage in self._stages.values()])})"
        )

    def add_stage(self, stage: BaseStage) -> None:
        """
        Add the stage to our graph

        :param func: The callable to be ran for this stage
        :param name: The name of the stage
        :param depends_on: The stages this stage depends on
        """
        self._stages[stage.name] = stage
        self._graph[stage.name] = OrderedSet()

        for dependency in stage.depends_on:
            self._graph[stage.name].add(dependency)

    def add_stages(self, stages: list[BaseStage]):
        """
        Add a list of stages to the Workflow

        :param stages: A list of Stages
        """
        for stage in stages:
            self.add_stage(stage)

    def __iter__(self):
        """
        Iterate through stages in a sorted order.
        """
        for group in topological_sort_grouped(self._graph):
            yield group

    def get_stage(self, stage_name: str) -> BaseStage:
        """
        Return the cooresponding Stage given
        a stage name.
        """
        return self._stages[stage_name]


def to_graph(workflow: WorkflowResource) -> WorkflowGraph:
    """
    Convert a WorkflowResource to a WorkflowGraph

    :param workflow: The WorkflowResource to convert
    :return: A WorkflowGraph
    """
    stages = []

    for stage in workflow.spec.stages:
        stages.append(BaseStage.from_definition(stage))

    return WorkflowGraph(stages)
