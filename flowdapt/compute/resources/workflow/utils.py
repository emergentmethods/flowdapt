from typing import Iterator

from flowdapt.lib.utils.misc import OrderedSet


def topological_sort(graph: dict[str, OrderedSet[str]]) -> list[str]:
    """
    Given a directed acylic graph with a structure like:
    {
        'first': {},
        'middle': {},
        'second': {'first'},
        'third': {'second', 'first'}
    }

    It will generate topologically sorted list of nodes:
        ['first', 'middle', 'second']
    """
    result: list[str] = []
    seen: OrderedSet[str] = OrderedSet()

    def recurse(node: str) -> None:
        for neighbor in graph.get(node, []):
            if neighbor not in seen:
                seen.add(neighbor)
                recurse(neighbor)
        if node not in result:
            result.append(node)

    for key in graph.keys():
        recurse(key)

    return result


def topological_sort_grouped(
    graph: dict[str, OrderedSet[str]]
) -> Iterator[OrderedSet[str]]:
    """
    Given a directed acylic graph with a structure like:
    {
        'first': {},
        'middle': {},
        'second': {'first'},
        'third': {'second', 'first'}
    }

    It will generate topologically sorted groups:
        {'first', 'middle'}
        {'second'}
        {'third'}
    """
    # Special case empty input.
    if len(graph) < 1:
        return

    # Copy the input so as to leave it unmodified.
    # Discard self-dependencies and copy two levels deep.
    graph = {
        item: OrderedSet(e for e in dep if e != item)
        for item, dep in graph.items()
    }

    while True:
        ordered = OrderedSet(item for item, dep in graph.items() if not dep)

        if not ordered:
            break

        yield ordered

        graph = {
            item: (dep - ordered)
            for item, dep in graph.items()
            if item not in ordered
        }

    assert not graph, ("Problematic stage dependency. "
                       f"Check your workflow defintion at stage: {graph}")


def is_valid_dag(graph: dict[str, OrderedSet[str]]) -> bool:
    """
    Iterate over the entire graph using topological_sort_grouped
    and check if an AssertionError is raised, True otherwise.

    :param graph: The graph to test
    """
    try:
        [group for group in topological_sort_grouped(graph)]
    except AssertionError:
        return False
    return True
