from netbox.api.viewsets import NetBoxModelViewSet

from .. import filtersets
from ..models import Equipment, EquipmentFlow, Plateau
from . import serializers


class PlateauViewSet(NetBoxModelViewSet):
    queryset = Plateau.objects.select_related('site').prefetch_related('tags')
    serializer_class = serializers.PlateauSerializer
    filterset_class = filtersets.PlateauFilterSet


class EquipmentViewSet(NetBoxModelViewSet):
    queryset = Equipment.objects.select_related(
        'site', 'plateau', 'location', 'manufacturer',
        'primary_ip', 'vlan', 'dcim_device',
    ).prefetch_related('applications', 'tags')
    serializer_class = serializers.EquipmentSerializer
    filterset_class = filtersets.EquipmentFilterSet


class EquipmentFlowViewSet(NetBoxModelViewSet):
    queryset = EquipmentFlow.objects.select_related(
        'source', 'target',
    ).prefetch_related('tags')
    serializer_class = serializers.EquipmentFlowSerializer
    filterset_class = filtersets.EquipmentFlowFilterSet
