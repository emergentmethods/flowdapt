import pytest
import asyncio
from datetime import datetime
from uuid import UUID
from pydantic.error_wrappers import ValidationError

from flowdapt.compute.domain.models.workflow import (
    WorkflowResource,
    WorkflowStage,
)
from flowdapt.compute.domain.dto.v1.workflow import (
    V1Alpha1WorkflowResourceCreateRequest,
)
from flowdapt.compute.resources.workflow.methods import (
    create_workflow,
    delete_workflow,
    get_workflow,
    list_workflows,
    run_workflow
)
from flowdapt.compute.resources.workflow.execute import execute_workflow


def get_workflow_create_payload(
    name: str,
    stages: list[dict] = [
        {"name": "test_stage_one", "target": "tests.compute.dummy_workflow_stages.test_stage_one"}
    ],
    validate: bool = True
):
    payload = {
        "metadata": {
            "name": name,
        },
        "spec": {"stages": stages}
    }

    if validate:
        return V1Alpha1WorkflowResourceCreateRequest(**payload)
    else:
        return payload


async def clear_workflows():
    for workflow in await list_workflows():
        await delete_workflow(workflow.name)


async def test_list_workflows(test_context):
    workflows = await list_workflows()
    assert workflows == []


async def test_create_workflow_from_payload(test_context, clear_db):
    name = "test_workflow"
    workflow_create_payload = get_workflow_create_payload(name)

    workflow = await create_workflow(workflow_create_payload.to_model())
    assert workflow is not None, workflow
    assert isinstance(workflow, WorkflowResource), workflow
    assert len(workflow.spec.stages) == 1, workflow
    assert isinstance(workflow.spec.stages[0], WorkflowStage), workflow
    assert workflow.spec.stages[0].name == 'test_stage_one', workflow
    assert workflow.spec.stages[0].target == 'tests.compute.dummy_workflow_stages.test_stage_one', workflow
    assert workflow.spec.stages[0].depends_on == [], workflow
    assert workflow.metadata.name == name, workflow
    assert isinstance(workflow.metadata.uid, UUID), workflow
    assert isinstance(workflow.metadata.updated_at, datetime), workflow
    assert isinstance(workflow.metadata.created_at, datetime), workflow

    workflows = await list_workflows()
    assert workflows == [workflow], workflows

    workflow_by_id = await get_workflow(workflow.metadata.uid)
    assert workflow_by_id == workflow, workflows

    workflow_by_name = await get_workflow(name)
    assert workflow_by_name == workflow, workflows


async def test_create_bad_workflow_no_stages(test_context, clear_db):
    name = "test_workflow"
    workflow_create_payload = get_workflow_create_payload(name)
    workflow_create_payload.spec.stages = []

    with pytest.raises(ValidationError):
        await create_workflow(workflow_create_payload.to_model())

    workflows = await list_workflows()
    assert workflows == [], workflows


async def test_create_bad_workflow_no_name(test_context, clear_db):
    name = ""
    workflow_create_payload = get_workflow_create_payload(name)

    with pytest.raises(ValidationError):
        await create_workflow(workflow_create_payload.to_model())

    workflows = await list_workflows()
    assert workflows == [], workflows


async def test_delete_workflow_by_id(test_context, clear_db):
    name = "test_workflow"
    workflow_create_payload = get_workflow_create_payload(name)

    workflows = await list_workflows()
    assert workflows == []

    workflow = await create_workflow(workflow_create_payload.to_model())
    assert workflow is not None, workflow

    workflows = await list_workflows()
    assert workflows == [workflow], workflows

    await delete_workflow(workflow.metadata.uid)

    workflows = await list_workflows()
    assert workflows == []


async def test_delete_workflow_by_name(test_context, clear_db):
    name = "test_workflow"
    workflow_create_payload = get_workflow_create_payload(name)

    workflows = await list_workflows()
    assert workflows == []

    workflow = await create_workflow(workflow_create_payload.to_model())
    assert workflow is not None, workflow

    workflows = await list_workflows()
    assert workflows == [workflow], workflows

    await delete_workflow(name)

    workflows = await list_workflows()
    assert workflows == []


async def test_run_workflow(test_context, clear_db):
    name = "test_workflow"
    test_stages = [
        {"name": "test_stage_one", "target": "tests.compute.dummy_workflow_stages.test_stage_one"},
        {"name": "test_stage_two", "target": "tests.compute.dummy_workflow_stages.test_stage_two"},
    ]
    workflow_create_payload = get_workflow_create_payload(name, stages=test_stages)
    workflow = await create_workflow(workflow_create_payload.to_model())

    assert workflow is not None, workflow

    workflow_run = await run_workflow(name, input={}, wait=True)

    assert workflow_run.finished_at is not None, workflow_run
    assert workflow_run.result == None, workflow_run
    assert isinstance(workflow_run.started_at, datetime), workflow_run
    assert isinstance(workflow_run.uid, UUID), workflow_run
    assert isinstance(workflow_run.name, str), workflow_run
    assert isinstance(workflow_run.state, str), workflow_run

    assert workflow_run.state == "finished", workflow_run


async def test_run_workflow_with_resources(test_context, clear_db):
    name = "test_workflow"
    test_stage = {"name": "test_stage_one", 
                  "target": "tests.compute.dummy_workflow_stages.test_stage_one",
                  "required_resources": ["threads=1","memory=4e9"]}
    workflow_create_payload = get_workflow_create_payload(name, stages=[test_stage])
    workflow = await create_workflow(workflow_create_payload.to_model())

    assert workflow is not None, workflow

    workflow_run = await run_workflow(name, input={}, wait=True)

    assert workflow_run.result == None, workflow_run    
    assert workflow_run.state == "finished", workflow_run

async def test_run_workflow_with_error(test_context, clear_db):
    name = "test_workflow"
    test_stage = {"name": "test_stage_error", 
                  "target": "tests.compute.dummy_workflow_stages.test_stage_error"}
    workflow_create_payload = get_workflow_create_payload(name, stages=[test_stage])
    workflow = await create_workflow(workflow_create_payload.to_model())

    assert workflow is not None, workflow

    workflow_run = await run_workflow(name, input={}, wait=True)

    assert workflow_run.result is not None, workflow_run    
    assert workflow_run.result[0] == "Exception", workflow_run
    assert workflow_run.state == "failed", workflow_run
    
