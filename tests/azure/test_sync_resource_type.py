import pytest

from django_q.tasks import fetch, async_task, result

from mce_django_app.models.common import ResourceType
from mce_django_app import constants

from mce_tasks_djq.azure import PROVIDERS

pytestmark = pytest.mark.django_db(transaction=True, reset_sequences=True)

def test_azure_sync_resource_type(broker):

    count_type = len(PROVIDERS)

    task_id = async_task(
        'mce_tasks_djq.azure.sync_resource_type', 
        broker=broker, sync=True)

    task = fetch(task_id)
    assert task.success is True, result(task_id)

    assert result(task_id) == dict(
        errors=0,
        created=count_type, 
        updated=0,
        deleted=0
    )

    assert ResourceType.objects.count() == count_type

    task = async_task(
        'mce_tasks_djq.azure.sync_resource_type', 
        broker=broker, sync=True)

    assert result(task) == dict(
        errors=0,
        created=0, 
        updated=count_type,
        deleted=0
    )
