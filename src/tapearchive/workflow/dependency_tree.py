from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from collections import defaultdict


class Stage(ABC):
    _dependencies: List["Type"] = []

    def __init__(self, name: str, **kwargs):
        self._name = name
        self._kwargs = kwargs

    @abstractmethod
    def do_fullfillment(self):
        pass

    @abstractmethod
    def is_done() -> bool:
        pass


class DependencyTreeBuilder:
    def __init__(self, pipeline: "DependencyTree", context_type: Type):
        self._pipeline = pipeline
        self._type = context_type

    def depends_on(self, *dependencies: Type):
        self._pipeline.add_dependecy(self._type, *dependencies)


class PipelineNode:
    def __init__(self, parent: Optional["PipelineNode"] = None) -> None:
        self._parent: Optional["PipelineNode"] = parent
        self._children = []
        self._stage = None

    def add_child(self, child: "PipelineNode"):
        self._children.append(child)

    def set_stage(self, stage: Stage):
        self._stage = stage
        pass

    def start_fullfillment(self):
        self._stage.start_fullfillment()

    def execute(self):
        for child in self._children:
            pass

    # TODO: Store/restore/recover?


def has_dependency_loop(tree: PipelineNode) -> bool:
    # Tortoise and Hare algorythm
    return False


class DependencyTree:
    def __init__(self):
        self._dependencies: Dict[Type, List[Type]] = defaultdict(list)

    def new_stage(self, stage_type: Type) -> DependencyTreeBuilder:
        self._dependencies[stage_type]
        return DependencyTreeBuilder(self, stage_type)

    def add_dependecy(self, stage_type: Type, *dependencies: Type):
        self._dependencies[stage_type].extend(dependencies)

    def build_pipeline_for(self, target_stage: Type, *args: Any, **kwargs: Any) -> PipelineNode:
        pipeline = PipelineNode()
        self._build_tree(target_stage, pipeline, args, kwargs)
        if has_dependency_loop(pipeline):
            raise RuntimeError("Cannot reate execution pipeline, it has a dependency loop.")
        return pipeline

    def _build_tree(self, target_stage: Type, node: PipelineNode, args, kwargs):
        node.set_stage(target_stage(*args, **kwargs))
        for sub_stage in self._dependencies.get(target_stage, []):
            child_node = PipelineNode(node)
            node.add_child(child_node)
            self._build_tree(sub_stage, child_node)
