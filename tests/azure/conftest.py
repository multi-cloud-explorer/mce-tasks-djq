from uuid import uuid4

import pytest
from ddf import G

pytestmark = pytest.mark.django_db(transaction=True, reset_sequences=True)

from mce_django_app import constants
from mce_django_app.models.common import GenericAccount, ResourceType
from mce_django_app.models import azure as models

@pytest.fixture
def generic_account():
    return G(GenericAccount)

@pytest.fixture
def subscription(generic_account):
    return models.Subscription.objects.create(
        id="00000000-0000-0000-0000-000000000000",
        name="sub1",
        tenant="00000000-0000-0000-0000-000000000000",
        location="francecentral",
        account=generic_account
    )

@pytest.fixture
def resource_type_azure_group():
    return ResourceType.objects.create(
        name="Microsoft.Resources/resourceGroups",
        provider=constants.Provider.AZURE
    )

@pytest.fixture
def resource_group(subscription, resource_type_azure_group):

    name = "MY_RG"
    resource_id = f"/subscriptions/{subscription.pk}/resourceGroups/{name}"
    #/providers/{resource_type_azure_group.name}/{name}
    #"id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/MY_RG",
    
    return models.ResourceGroupAzure.objects.create(
        id=resource_id,
        name=name,
        resource_type=resource_type_azure_group,
        subscription=subscription,
        provider=constants.Provider.AZURE,
        location="francecentral",
    )

