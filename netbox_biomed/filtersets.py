import django_filters
from dcim.models import Manufacturer, Site
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from netbox.filtersets import NetBoxModelFilterSet

from .choices import (
    ConnectionModeChoices,
    CriticalityChoices,
    DeviceClassChoices,
    EquipmentRoleChoices,
    EquipmentStatusChoices,
    FlowStatusChoices,
    NetworkExposureChoices,
    PlateauCategoryChoices,
)
from .models import Equipment, EquipmentFlow, Plateau


class PlateauFilterSet(NetBoxModelFilterSet):
    site_id = django_filters.ModelMultipleChoiceFilter(
        field_name='site',
        queryset=Site.objects.all(),
        label=_('Establishment (ID)'),
    )
    category = django_filters.MultipleChoiceFilter(
        choices=PlateauCategoryChoices,
    )

    class Meta:
        model = Plateau
        fields = ('id', 'name', 'manager')

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) | Q(description__icontains=value)
        )


class EquipmentFilterSet(NetBoxModelFilterSet):
    site_id = django_filters.ModelMultipleChoiceFilter(
        field_name='site',
        queryset=Site.objects.all(),
        label=_('Establishment (ID)'),
    )
    plateau_id = django_filters.ModelMultipleChoiceFilter(
        field_name='plateaux',
        queryset=Plateau.objects.all(),
        label=_('Technical platform (ID)'),
    )
    manufacturer_id = django_filters.ModelMultipleChoiceFilter(
        field_name='manufacturer',
        queryset=Manufacturer.objects.all(),
        label=_('Manufacturer (ID)'),
    )
    role = django_filters.MultipleChoiceFilter(choices=EquipmentRoleChoices)
    category = django_filters.MultipleChoiceFilter(choices=PlateauCategoryChoices)
    status = django_filters.MultipleChoiceFilter(choices=EquipmentStatusChoices)
    criticality = django_filters.MultipleChoiceFilter(choices=CriticalityChoices)
    device_class = django_filters.MultipleChoiceFilter(choices=DeviceClassChoices)
    network_exposure = django_filters.MultipleChoiceFilter(choices=NetworkExposureChoices)
    connection_mode = django_filters.MultipleChoiceFilter(choices=ConnectionModeChoices)
    remote_maintenance = django_filters.BooleanFilter()
    os_obsolete = django_filters.BooleanFilter(
        method='filter_os_obsolete',
        label=_('OS out of support'),
    )
    has_ip = django_filters.BooleanFilter(
        method='filter_has_ip',
        label=_('Has an IP address'),
    )

    class Meta:
        model = Equipment
        fields = (
            'id', 'name', 'gmao_id', 'mercator_id', 'serial', 'hostname',
            'ae_title', 'mac_address', 'os', 'edr', 'owner', 'care_unit',
        )

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value)
            | Q(description__icontains=value)
            | Q(model__icontains=value)
            | Q(serial__icontains=value)
            | Q(gmao_id__icontains=value)
            | Q(hostname__icontains=value)
            | Q(ae_title__icontains=value)
        )

    def filter_os_obsolete(self, queryset, name, value):
        today = timezone.now().date()
        if value:
            return queryset.filter(end_of_support__lt=today)
        return queryset.filter(
            Q(end_of_support__gte=today) | Q(end_of_support__isnull=True)
        )

    def filter_has_ip(self, queryset, name, value):
        return queryset.filter(primary_ip__isnull=not value)


class EquipmentFlowFilterSet(NetBoxModelFilterSet):
    source_id = django_filters.ModelMultipleChoiceFilter(
        field_name='source',
        queryset=Equipment.objects.all(),
        label=_('Source (ID)'),
    )
    target_id = django_filters.ModelMultipleChoiceFilter(
        field_name='target',
        queryset=Equipment.objects.all(),
        label=_('Target (ID)'),
    )
    equipment_id = django_filters.ModelMultipleChoiceFilter(
        method='filter_equipment',
        queryset=Equipment.objects.all(),
        label=_('Equipment (source or target)'),
    )
    status = django_filters.MultipleChoiceFilter(choices=FlowStatusChoices)
    encrypted = django_filters.BooleanFilter()
    monitored = django_filters.BooleanFilter(
        method='filter_monitored',
        label=_('Monitored (PRTG)'),
    )

    class Meta:
        model = EquipmentFlow
        fields = ('id', 'name', 'protocol', 'message_type', 'port', 'eai')

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value)
            | Q(protocol__icontains=value)
            | Q(message_type__icontains=value)
            | Q(description__icontains=value)
            | Q(source__name__icontains=value)
            | Q(target__name__icontains=value)
        )

    def filter_equipment(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(Q(source__in=value) | Q(target__in=value))

    def filter_monitored(self, queryset, name, value):
        if value:
            return queryset.exclude(prtg_sensor='')
        return queryset.filter(prtg_sensor='')
