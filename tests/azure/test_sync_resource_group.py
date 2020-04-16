from unittest.mock import patch

import pytest
import requests

from django_q.tasks import fetch, async_task, result

from mce_django_app.models.common import ResourceEventChange
from mce_django_app.models.azure import ResourceGroupAzure
from mce_django_app import constants

pytestmark = pytest.mark.django_db(transaction=True, reset_sequences=True)

@patch("mce_tasks_djq.azure.get_subscription_and_session")
@patch("requests.Session.get")
def test_azure_sync_resource_group_create(
    session_get_func,
    get_subscription_and_session_func,
    mock_response_class, json_file, subscription, broker,
    mce_app_resource_type_azure_group):
    """Create 2 resources group and create changes events"""

    data = json_file("resource_group_list.json")
    count_groups = len(data['value'])
    get_subscription_and_session_func.return_value = (subscription, requests.Session())
    
    session_get_func.return_value = mock_response_class(200, data)

    task_id = async_task(
        'mce_tasks_djq.azure.sync_resource_group', 
        subscription.pk,
        task_name='test.azure.sync.resource_group',
        broker=broker, sync=True)

    task = fetch(task_id)
    assert task.success is True, result(task_id)
    assert result(task_id) == dict(
        errors=0,
        created=count_groups, 
        updated=0,
        deleted=0
    )

    assert ResourceGroupAzure.objects.count() == count_groups

    assert ResourceEventChange.objects.filter(
        action=constants.EventChangeType.CREATE).count() == count_groups

@patch("mce_tasks_djq.azure.get_subscription_and_session")
@patch("requests.Session.get")
def test_azure_sync_resource_group_update(
    session_get_func,
    get_subscription_and_session_func,
    mock_response_class, json_file, subscription, broker,
    mce_app_resource_type_azure_group):
    """Update 1 resource group and create change event"""

    assert ResourceGroupAzure.all_objects.count() == 0
    assert ResourceEventChange.all_objects.count() == 0

    data = json_file("resource_group_list.json")
    get_subscription_and_session_func.return_value = (subscription, requests.Session())

    # Create
    session_get_func.return_value = mock_response_class(200, data)
    task_id = async_task(
        'mce_tasks_djq.azure.sync_resource_group', 
        subscription.pk,
        broker=broker, sync=True)
    task = fetch(task_id)
    assert task.success is True, result(task_id)
    assert result(task_id) == dict(
        errors=0,
        created=2, 
        updated=0,
        deleted=0
    )
    assert ResourceGroupAzure.all_objects.count() == 2

    # Update one
    data['value'][0]['tags']["testtag"] = "TEST"
    session_get_func.return_value = mock_response_class(200, data)

    task_id = async_task(
        'mce_tasks_djq.azure.sync_resource_group', 
        subscription.pk,
        task_name='test.azure.sync.resource_group',
        broker=broker, sync=True)

    task = fetch(task_id)
    assert task.success is True, result(task_id)
    assert result(task_id) == dict(
        errors=0,
        created=0, 
        updated=1,
        deleted=0
    )

    assert ResourceEventChange.objects.filter(
        action=constants.EventChangeType.UPDATE).count() == 1

@patch("mce_tasks_djq.azure.get_subscription_and_session")
@patch("requests.Session.get")
def test_azure_sync_resource_group_delete(
    session_get_func,
    get_subscription_and_session_func,
    mock_response_class, json_file, subscription, broker,
    mce_app_resource_type_azure_group):
    """Delete 2 resource group and create change events"""

    data = json_file("resource_group_list.json")
    count_groups = len(data['value'])
    get_subscription_and_session_func.return_value = (subscription, requests.Session())

    # Create
    session_get_func.return_value = mock_response_class(200, data)
    task_id = async_task(
        'mce_tasks_djq.azure.sync_resource_group', 
        subscription.pk,
        broker=broker, sync=True)
    task = fetch(task_id)
    assert task.success is True, result(task_id)
    assert result(task_id) == dict(
        errors=0,
        created=2, 
        updated=0,
        deleted=0
    )
    assert ResourceGroupAzure.all_objects.count() == 2

    # Delete
    session_get_func.return_value = mock_response_class(200, {"value": []})

    task_id = async_task(
        'mce_tasks_djq.azure.sync_resource_group', 
        subscription.pk,
        task_name='test.azure.sync.resource_group',
        broker=broker, sync=True)

    task = fetch(task_id)
    assert task.success is True, result(task_id)
    assert result(task_id) == dict(
        errors=0,
        created=0, 
        updated=0,
        deleted=count_groups
    )

    assert ResourceEventChange.objects.filter(
        action=constants.EventChangeType.DELETE).count() == count_groups

    assert ResourceGroupAzure.objects.count() == 0
    assert ResourceGroupAzure.all_objects.count() == count_groups


