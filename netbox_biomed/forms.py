from dcim.models import Device, Location, Manufacturer, Site
from django import forms
from django.utils.translation import gettext_lazy as _
from ipam.models import VLAN, IPAddress
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from netbox_it_landscape.models import Application
from utilities.forms import BOOLEAN_WITH_BLANK_CHOICES
from utilities.forms.fields import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    TagFilterField,
)
from utilities.forms.rendering import FieldSet

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

#
# Plateaux techniques
#

class PlateauForm(NetBoxModelForm):
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        label=_('Establishment'),
    )

    class Meta:
        model = Plateau
        fields = ('site', 'name', 'category', 'manager', 'description', 'tags')


class PlateauFilterForm(NetBoxModelFilterSetForm):
    model = Plateau
    site_id = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label=_('Establishment'),
    )
    category = forms.MultipleChoiceField(
        choices=PlateauCategoryChoices,
        required=False,
        label=_('Category'),
    )
    tag = TagFilterField(model)


#
# Équipements
#

class EquipmentForm(NetBoxModelForm):
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        label=_('Establishment'),
    )
    plateau = DynamicModelChoiceField(
        queryset=Plateau.objects.all(),
        required=False,
        label=_('Technical platform'),
        query_params={'site_id': '$site'},
    )
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        label=_('Location (room)'),
        query_params={'site_id': '$site'},
    )
    manufacturer = DynamicModelChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
        label=_('Manufacturer'),
    )
    primary_ip = DynamicModelChoiceField(
        queryset=IPAddress.objects.all(),
        required=False,
        label=_('Primary IP'),
    )
    vlan = DynamicModelChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        label=_('VLAN'),
    )
    dcim_device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        required=False,
        label=_('DCIM device'),
    )
    applications = DynamicModelMultipleChoiceField(
        queryset=Application.objects.all(),
        required=False,
        label=_('Applications fed'),
    )

    fieldsets = (
        FieldSet(
            'name', 'role', 'status', 'description', 'tags',
            name=_('Identity'),
        ),
        FieldSet(
            'category', 'device_class', 'criticality',
            name=_('Classification'),
        ),
        FieldSet(
            'site', 'plateau', 'location', 'care_unit',
            name=_('Attachment'),
        ),
        FieldSet(
            'manufacturer', 'model', 'serial', 'gmao_id', 'commissioning_date',
            name=_('Hardware / fleet'),
        ),
        FieldSet(
            'primary_ip', 'mac_address', 'hostname', 'ae_title', 'listen_ports',
            'vlan', 'connection_mode', 'ssid', 'dcim_device',
            name=_('Network'),
        ),
        FieldSet(
            'os', 'end_of_support', 'edr', 'edr_exclusions',
            'vendor_account', 'vault_ref',
            'remote_maintenance', 'remote_maintenance_mode', 'network_exposure',
            name=_('Cyber posture'),
        ),
        FieldSet(
            'applications', 'owner', 'mercator_id',
            name=_('Functional links'),
        ),
    )

    class Meta:
        model = Equipment
        fields = (
            'name', 'role', 'status', 'description',
            'category', 'device_class', 'criticality',
            'site', 'plateau', 'location', 'care_unit',
            'manufacturer', 'model', 'serial', 'gmao_id', 'commissioning_date',
            'primary_ip', 'mac_address', 'hostname', 'ae_title', 'listen_ports',
            'vlan', 'connection_mode', 'ssid', 'dcim_device',
            'os', 'end_of_support', 'edr', 'edr_exclusions',
            'vendor_account', 'vault_ref',
            'remote_maintenance', 'remote_maintenance_mode', 'network_exposure',
            'applications', 'owner', 'mercator_id', 'comments', 'tags',
        )


class EquipmentFilterForm(NetBoxModelFilterSetForm):
    model = Equipment
    site_id = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label=_('Establishment'),
    )
    plateau_id = DynamicModelMultipleChoiceField(
        queryset=Plateau.objects.all(),
        required=False,
        label=_('Technical platform'),
    )
    manufacturer_id = DynamicModelMultipleChoiceField(
        queryset=Manufacturer.objects.all(),
        required=False,
        label=_('Manufacturer'),
    )
    role = forms.MultipleChoiceField(
        choices=EquipmentRoleChoices,
        required=False,
        label=_('Role'),
    )
    category = forms.MultipleChoiceField(
        choices=PlateauCategoryChoices,
        required=False,
        label=_('Category'),
    )
    status = forms.MultipleChoiceField(
        choices=EquipmentStatusChoices,
        required=False,
        label=_('Status'),
    )
    criticality = forms.MultipleChoiceField(
        choices=CriticalityChoices,
        required=False,
        label=_('Criticality'),
    )
    device_class = forms.MultipleChoiceField(
        choices=DeviceClassChoices,
        required=False,
        label=_('Device class'),
    )
    network_exposure = forms.MultipleChoiceField(
        choices=NetworkExposureChoices,
        required=False,
        label=_('Network exposure'),
    )
    connection_mode = forms.MultipleChoiceField(
        choices=ConnectionModeChoices,
        required=False,
        label=_('Connection mode'),
    )
    os_obsolete = forms.NullBooleanField(
        required=False,
        label=_('OS out of support'),
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    remote_maintenance = forms.NullBooleanField(
        required=False,
        label=_('Vendor remote maintenance'),
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    has_ip = forms.NullBooleanField(
        required=False,
        label=_('Has an IP address'),
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)


#
# Flux
#

class EquipmentFlowForm(NetBoxModelForm):
    source = DynamicModelChoiceField(
        queryset=Equipment.objects.all(),
        label=_('Source'),
    )
    target = DynamicModelChoiceField(
        queryset=Equipment.objects.all(),
        label=_('Target'),
    )

    fieldsets = (
        FieldSet(
            'name', 'source', 'target', 'protocol', 'message_type', 'port',
            'encrypted', 'status', 'description', 'tags',
            name=_('Flow'),
        ),
        FieldSet(
            'eai', 'source_endpoint', 'eai_endpoint', 'target_endpoint',
            name=_('Endpoints'),
        ),
        FieldSet(
            'prtg_sensor', 'recovery_procedure', 'vendor_contact',
            name=_('Operations'),
        ),
    )

    class Meta:
        model = EquipmentFlow
        fields = (
            'name', 'source', 'target', 'protocol', 'message_type', 'port',
            'encrypted', 'status', 'eai',
            'source_endpoint', 'eai_endpoint', 'target_endpoint',
            'prtg_sensor', 'recovery_procedure', 'vendor_contact',
            'description', 'tags',
        )


class EquipmentFlowFilterForm(NetBoxModelFilterSetForm):
    model = EquipmentFlow
    source_id = DynamicModelMultipleChoiceField(
        queryset=Equipment.objects.all(),
        required=False,
        label=_('Source'),
    )
    target_id = DynamicModelMultipleChoiceField(
        queryset=Equipment.objects.all(),
        required=False,
        label=_('Target'),
    )
    protocol = forms.CharField(required=False, label=_('Protocol'))
    status = forms.MultipleChoiceField(
        choices=FlowStatusChoices,
        required=False,
        label=_('Status'),
    )
    encrypted = forms.NullBooleanField(
        required=False,
        label=_('Encrypted'),
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    monitored = forms.NullBooleanField(
        required=False,
        label=_('Monitored (PRTG)'),
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)
