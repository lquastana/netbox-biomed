from dcim.api.serializers import (
    DeviceSerializer,
    LocationSerializer,
    ManufacturerSerializer,
    SiteSerializer,
)
from ipam.api.serializers import IPAddressSerializer, VLANSerializer
from netbox.api.fields import SerializedPKRelatedField
from netbox.api.serializers import NetBoxModelSerializer
from netbox_it_landscape.api.serializers import ApplicationSerializer
from netbox_it_landscape.models import Application
from rest_framework import serializers

from ..models import Equipment, EquipmentFlow, Plateau


class PlateauSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netbox_biomed-api:plateau-detail',
    )
    site = SiteSerializer(nested=True)

    class Meta:
        model = Plateau
        fields = (
            'id', 'url', 'display', 'site', 'name', 'category', 'manager',
            'description', 'tags', 'custom_fields', 'created', 'last_updated',
        )
        brief_fields = ('id', 'url', 'display', 'name')


class EquipmentSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netbox_biomed-api:equipment-detail',
    )
    site = SiteSerializer(nested=True)
    # M2M modifiables par identifiants (un nested serializer seul est read-only)
    plateaux = SerializedPKRelatedField(
        queryset=Plateau.objects.all(),
        serializer=PlateauSerializer,
        nested=True,
        required=False,
        many=True,
    )
    location = LocationSerializer(nested=True, required=False, allow_null=True)
    manufacturer = ManufacturerSerializer(nested=True, required=False, allow_null=True)
    primary_ip = IPAddressSerializer(nested=True, required=False, allow_null=True)
    vlan = VLANSerializer(nested=True, required=False, allow_null=True)
    dcim_device = DeviceSerializer(nested=True, required=False, allow_null=True)
    applications = SerializedPKRelatedField(
        queryset=Application.objects.all(),
        serializer=ApplicationSerializer,
        nested=True,
        required=False,
        many=True,
    )
    os_obsolete = serializers.BooleanField(read_only=True)

    class Meta:
        model = Equipment
        fields = (
            'id', 'url', 'display', 'name', 'role', 'description',
            'category', 'device_class', 'criticality', 'status',
            'site', 'plateaux', 'location', 'care_unit',
            'manufacturer', 'model', 'serial', 'gmao_id', 'mercator_id',
            'commissioning_date',
            'primary_ip', 'mac_address', 'hostname', 'ae_title',
            'listen_ports', 'vlan', 'connection_mode', 'ssid', 'dcim_device',
            'os', 'end_of_support', 'os_obsolete', 'edr', 'edr_exclusions',
            'vendor_account', 'vault_ref',
            'remote_maintenance', 'remote_maintenance_mode', 'network_exposure',
            'applications', 'owner', 'comments',
            'tags', 'custom_fields', 'created', 'last_updated',
        )
        brief_fields = ('id', 'url', 'display', 'name', 'role')


class EquipmentFlowSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netbox_biomed-api:equipmentflow-detail',
    )
    source = EquipmentSerializer(nested=True)
    target = EquipmentSerializer(nested=True)

    class Meta:
        model = EquipmentFlow
        fields = (
            'id', 'url', 'display', 'name', 'source', 'target',
            'protocol', 'message_type', 'port', 'encrypted', 'status',
            'eai', 'source_endpoint', 'eai_endpoint', 'target_endpoint',
            'prtg_sensor', 'recovery_procedure', 'vendor_contact',
            'description', 'tags', 'custom_fields', 'created', 'last_updated',
        )
        brief_fields = ('id', 'url', 'display', 'name')
