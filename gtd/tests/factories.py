# Test data factories — factory_boy definitions
import factory
from django.contrib.auth.models import User

from gtd.models import (
    Action,
    Area,
    Context,
    Domain,
    InboxItem,
    Priority,
    Project,
    Status,
    WorkSession,
)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda o: f'{o.username}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')


class DomainFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Domain

    name = factory.Sequence(lambda n: f'Domain {n}')
    color = 'primary'
    user = factory.SubFactory(UserFactory)


class AreaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Area

    name = factory.Sequence(lambda n: f'Area {n}')
    domain = factory.SubFactory(DomainFactory)
    user = factory.LazyAttribute(lambda o: o.domain.user)


class StatusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Status

    name = factory.Sequence(lambda n: f'Status {n}')
    activity_level = factory.Sequence(lambda n: n)


class PriorityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Priority

    name = factory.Sequence(lambda n: f'Priority {n}')
    rank = factory.Sequence(lambda n: n)


class ContextFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Context

    name = factory.Sequence(lambda n: f'Context {n}')
    user = factory.SubFactory(UserFactory)


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project

    name = factory.Sequence(lambda n: f'Project {n}')
    area = factory.SubFactory(AreaFactory)
    user = factory.LazyAttribute(lambda o: o.area.user)
    status = factory.LazyFunction(lambda: Status.objects.get_or_create(
        name='IN ACTION', defaults={'activity_level': 6, 'color': 'success'},
    )[0])


class ActionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Action

    name = factory.Sequence(lambda n: f'Action {n}')
    project = factory.SubFactory(ProjectFactory)
    area = factory.LazyAttribute(lambda o: o.project.area)
    user = factory.LazyAttribute(lambda o: o.project.user)
    priority = factory.LazyFunction(lambda: Priority.objects.get_or_create(
        name='Medium', defaults={'rank': 3},
    )[0])


class InboxItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InboxItem

    item = factory.Sequence(lambda n: f'Inbox item {n}')
    user = factory.SubFactory(UserFactory)


class WorkSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkSession

    action = factory.SubFactory(ActionFactory)
    user = factory.LazyAttribute(lambda o: o.action.user)
    started_at = factory.LazyFunction(lambda: __import__('django.utils.timezone', fromlist=['now']).now())
