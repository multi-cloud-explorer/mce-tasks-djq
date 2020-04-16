import copy
import logging
import json
import jsonpatch

from django_q.tasks import schedule
from django_q.models import Schedule
from django_q.tasks import async_task, result

# from django.core.signals import request_finished
# request_finished.send(sender="greenlet")

from mce_azure.utils import get_access_token
from mce_azure import core as cli
from mce_azure.core import PROVIDERS

from mce_django_app.models.common import ResourceEventChange, Tag, ResourceType
from mce_django_app import constants
from mce_django_app.models import azure as models

logger = logging.getLogger(__name__)


def get_subscription_and_session(subscription_id):
    # TODO: raise if active=False
    subscription = models.Subscription.objects.get(subscription_id=subscription_id)
    auth = subscription.get_auth()
    token = get_access_token(**auth)
    session = cli.get_session(token=token['access_token'])
    return subscription, session


def create_event_change_create(new_resource):
    """CREATE Event for ResourceAzure and ResourceGroupAzure"""

    return ResourceEventChange.objects.create(
        action=constants.EventChangeType.CREATE,
        content_object=new_resource,
        new_object=new_resource.to_dict(exclude=['created', 'updated']),
    )


def create_event_change_update(old_obj, new_resource):
    """UPDATE Event for ResourceAzure and ResourceGroupAzure"""

    new_obj = new_resource.to_dict(exclude=["created", "updated"])

    patch = jsonpatch.JsonPatch.from_diff(old_obj, new_obj)

    if patch.patch:
        msg = f"create event change update for {old_obj['resource_id']}"
        logger.info(msg)

        return ResourceEventChange.objects.create(
            action=constants.EventChangeType.UPDATE,
            content_object=new_resource,
            changes=list(patch),
            old_object=old_obj,
            new_object=new_obj,
            diff=None,
        )


def create_event_change_delete(queryset):
    """DELETE Event for ResourceAzure and ResourceGroupAzure"""

    for doc in queryset:
        ResourceEventChange.objects.create(
            action=constants.EventChangeType.DELETE,
            content_object=doc,
            old_object=doc.to_dict(exclude=['created', 'updated']),
        )


def sync_resource_group(subscription_id):

    subscription, session = get_subscription_and_session(subscription_id)
    resources_groups = cli.get_resourcegroups_list(subscription_id, session=session)
    company = subscription.company
    #users = company.user_set.all()

    _created = 0
    _updated = 0
    _errors = 0
    _deleted = 0

    found_ids = []

    for r in resources_groups:

        resource_id = r['id'].lower()
        found_ids.append(resource_id)

        _type = ResourceType.objects.filter(
            name__iexact=r['type'], provider=constants.Provider.AZURE
        ).first()

        if not _type:
            _errors += 1
            msg = f"resource type [{r['type']}] not found - bypass resource [{resource_id}]"
            logger.error(msg)
            continue

        # TODO: ajouter autres champs ?
        metas = r.get('properties', {}) or {}

        tags_objects = []

        # TODO: events et logs
        tags = r.get('tags', {}) or {}
        for k, v in tags.items():
            tag, created = Tag.objects.update_or_create(
                name=k, provider=constants.Provider.AZURE, defaults=dict(value=v)
            )
            tags_objects.append(tag)
            # if created: todo event tag

        old_resource = models.ResourceGroupAzure.objects.filter(resource_id=resource_id).first()
        old_object = None
        if old_resource:
            old_object = old_resource.to_dict(exclude=["created", "updated"])

        new_resource, created = models.ResourceGroupAzure.objects.update_or_create(
            resource_id=resource_id,
            defaults=dict(
                name=r['name'],  # TODO: lower ?
                subscription=subscription,
                company=company,
                resource_type=_type,
                location=r['location'],
                provider=constants.Provider.AZURE,
                metas=metas,
            ),
        )
        if tags_objects:
            new_resource.tags.set(tags_objects)

        if created:
            _created += 1
            #create_event_change_create(new_resource)
        else:
            changes = create_event_change_update(old_object, new_resource)
            if changes:
                _updated += 1

    logger.info(
        "sync - azure - ResourceGroupAzure - _errors[%s] - created[%s]- updated[%s]"
        % (_errors, _created, _updated)
    )

    # Create events delete
    qs = models.ResourceGroupAzure.objects.exclude(
        resource_id__in=found_ids, subscription=subscription
    )
    create_event_change_delete(qs)

    # Mark for deleted
    qs = models.ResourceGroupAzure.objects.exclude(
        resource_id__in=found_ids, subscription=subscription
    )
    _deleted = qs.delete()

    logger.info(f"mark for deleted. [{_deleted}] old ResourceGroupAzure")

    # TODO: répercuter deleted sur les ressources rattachés ?
    # doc.resourceazure_set.all()
    # voir si déjà fait au niveau resource !

    return dict(errors=_errors, created=_created, updated=_updated, deleted=_deleted)


def sync_resource(subscription_id):
    """
    TODO: faire une version qui créer une async_task pour chaque resource
    1. fetch resource by id
    2. db + event
    > pas de gevent dans ce cas car parallélisme assurer par django-q
    """

    subscription, session = get_subscription_and_session(subscription_id)
    company = subscription.company

    _created = 0
    _updated = 0
    _errors = 0
    _deleted = 0

    found_ids = []

    for r in cli.get_resources_list(subscription_id, session):

        resource_id = r['id'].lower()
        found_ids.append(resource_id)

        product_type = r['type']
        if '|' in product_type:
            product_type = product_type.split('|')[0]

        _type = ResourceType.objects.filter(
            name__iexact=product_type, provider=constants.Provider.AZURE
        ).first()

        if not _type:
            msg = f"resource type [{product_type}] not found - bypass resource [{resource_id}]"
            logger.error(msg)
            _errors += 1
            continue

        group_name = resource_id.split('/')[4]
        group_id = f"/subscriptions/{subscription.subscription_id}/resourceGroups/{group_name}"
        # TODO: ajout company et subscription au filtre
        group = models.ResourceGroupAzure.objects.filter(resource_id__iexact=group_id).first()

        if not group:
            msg = f"resource group [{group_id}] not found - bypass resource [{resource_id}]"
            logger.error(msg)
            _errors += 1
            continue

        try:
            resource = cli.get_resource_by_id(resource_id, session=session)
        except Exception as err:
            msg = f"fetch resource {resource_id} error : {err}"
            logger.exception(msg)
            _errors += 1
            continue

        metas = resource.get('properties', {}) or {}

        tags_objects = []

        datas = dict(
            name=resource['name'],
            subscription=subscription,
            company=company,
            resource_type=_type,
            location=resource.get('location'),
            provider=constants.Provider.AZURE,
            resource_group=group,
            metas=metas,
        )

        if resource.get('sku'):
            datas['sku'] = resource.get('sku')

        if resource.get('kind'):
            datas['kind'] = resource.get('kind')

        tags = resource.get('tags', {}) or {}
        for k, v in tags.items():
            tag, created = Tag.objects.update_or_create(
                name=k, provider=constants.Provider.AZURE, defaults=dict(value=v)
            )
            tags_objects.append(tag)
            # if created: todo event tag

        old_resource = models.ResourceAzure.objects.filter(resource_id=resource_id).first()
        old_object = None
        if old_resource:
            old_object = old_resource.to_dict(exclude=["created", "updated"])

        new_resource, created = models.ResourceAzure.objects.update_or_create(
            resource_id=resource_id, defaults=datas
        )

        if tags_objects:
            new_resource.tags.set(tags_objects)

        if created:
            _created += 1
            #create_event_change_create(new_resource)
        else:
            changes = create_event_change_update(old_object, new_resource)
            if changes:
                _updated += 1

    logger.info(
        "sync - azure - ResourceAzure - errors[%s] - created[%s]- updated[%s]"
        % (_errors, _created, _updated)
    )

    # Create events delete
    qs = models.ResourceAzure.objects.exclude(
        resource_id__in=found_ids, subscription=subscription
    )
    create_event_change_delete(qs)

    qs = models.ResourceAzure.objects.exclude(
        resource_id__in=found_ids, subscription=subscription
    )
    _deleted = qs.delete()

    logger.info("mark for deleted. [%s] old ResourceAzure" % _deleted)

    return dict(errors=_errors, created=_created, updated=_updated, deleted=_deleted)


def sync_resource_type():

    _created = 0
    _updated = 0
    _errors = 0
    _deleted = 0

    # found_ids = []

    # TODO: use batch insert !
    
    for k, v in PROVIDERS.items():
        r, created = ResourceType.objects.update_or_create(
            name=k, defaults=dict(provider=constants.Provider.AZURE)
        )
        # found_ids.append(r.pk)

        if created:
            _created += 1
        else:
            _updated += 1

    logger.info(
        "sync - azure - ResourceType - errors[%s] - created[%s]- updated[%s]"
        % (_errors, _created, _updated)
    )

    # TODO: delete ???

    return dict(errors=_errors, created=_created, updated=_updated, deleted=_deleted)

def create_subscriptions_tasks():

    """
    task_name = "az-sync-resource-type"
    func = 'mce_tasks_djq.azure.sync_resource_type'

    _filter = dict(name=task_name, func=func)
    if Schedule.objects.filter(**_filter).first():
        continue

    schedule(
        func,
        subscription_id,
        name=task_name,
        schedule_type=Schedule.DAILY,
        #minutes=86400,
    )
    """

    subscriptions = models.Subscription.objects.filter(active=True)

    for subscription in subscriptions:

        subscription_id = subscription.subscription_id

        task_name = f"{subscription_id} : az-sync-resource-group"
        func = 'mce_tasks_djq.azure.sync_resource_group'

        _filter = dict(name=task_name, func=func)
        if Schedule.objects.filter(**_filter).first():
            # TODO: update schedule_type and minutes
            continue

        # TODO: settings

        # "('54d87296-b91a-47cd-93dd-955bd57b3e9a',)"
        schedule(
            func,
            subscription_id,
            name=task_name,
            schedule_type=Schedule.MINUTES,
            minutes=60,
        )

        task_name = f"{subscription_id} : az-sync-resources"
        func = 'mce_tasks_djq.azure.sync_resource'

        _filter = dict(name=task_name, func=func)
        if Schedule.objects.filter(**_filter).first():
            # TODO: update schedule_type and minutes
            continue

        # TODO: settings 
        # TODO: il faut que ce soit après les groups !!!
        schedule(
            func, 
            subscription_id,
            name=task_name,
            schedule_type=Schedule.MINUTES,
            minutes=30)


