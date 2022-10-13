import pytest
from tapearchive.workflow.dependency_tree import DependencyTree, Stage


class DummyStage(Stage):
    def _start_fullfillment(self):
        pass

    def _is_done()->bool:
        return True

class SecondDummyStage(Stage):
    def _start_fullfillment(self):
        pass

    def _is_done()->bool:
        return True


@pytest.mark.skip("Not yet implemented")
def test_pipeline_execution():
    pipeline = DependencyTree("test_pipeline")
    pipeline.new_stage(DummyStage).depends_on(SecondDummyStage)
    
    input_objects = []
    for obj in input_objects:
        execution_pipe = pipeline.build_pipeline_for(DummyStage, obj)
        execution_pipe.execute_all()
