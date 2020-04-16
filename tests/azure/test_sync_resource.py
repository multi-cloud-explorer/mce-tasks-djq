from unittest.mock import patch

import pytest
import requests

from django_q.tasks import fetch, async_task, result

from mce_django_app.models.common import ResourceEventChange, ResourceType
from mce_django_app.models.azure import ResourceAzure, ResourceGroupAzure
from mce_django_app import constants

@pytest.fixture
def require_resource_types():
    return [
        ResourceType.objects.create(
            name="Microsoft.Compute/virtualMachines",
            provider=constants.Provider.AZURE
        )
    ]

# TODO: gérer erreur retry et autre pendant le chargement d'une ressource    
# TODO: gérer product type avec | comme "Type": "Microsoft.Sql/servers/databases|v12.0,user",
# le v12.0,user: devient le kind
# TODO: name avec / comme "name": "samplesqlserver01/sample-azure-mssql"

@patch("mce_azure.core.get_resources_list")
@patch("mce_azure.core.get_resource_by_id")
@patch("mce_tasks_djq.azure.get_subscription_and_session")
def test_azure_sync_resource_create(
    get_subscription_and_session,
    get_resource_by_id,
    get_resources_list,
    mock_response_class, 
    json_file, 
    subscription,
    resource_group,
    broker,
    require_resource_types):

    #resource_group = mce_app_azure_resource_group

    data_resource_list = json_file("resource-list.json")
    data_resource = json_file("resource-vm.json")

    """
    resource_id = data_resource['id']
    group_name = resource_id.split('/')[4]
    group_id = f"/subscriptions/{subscription.pk}/resourceGroups/{group_name}"
    group = ResourceGroupAzure.objects.get(id__iexact=group_id)
    """
    
    count = len(data_resource_list['value'])
    get_subscription_and_session.return_value = (subscription, requests.Session())
    get_resources_list.return_value = data_resource_list['value']
    get_resource_by_id.return_value = data_resource

    task_id = async_task(
        'mce_tasks_djq.azure.sync_resource', 
        subscription.pk,
        task_name='test.azure.sync.resource',
        broker=broker, sync=True)

    task = fetch(task_id)
    assert task.success is True, result(task_id)
    assert result(task_id) == dict(
        errors=0,
        created=count, 
        updated=0,
        deleted=0
    )

    assert ResourceAzure.objects.count() == count

    assert ResourceEventChange.objects.filter(
        action=constants.EventChangeType.CREATE).count() == count + 1 # ResourceGroup

