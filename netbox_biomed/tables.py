import django_tables2 as tables
from django.utils.translation import gettext_lazy as _
from netbox.tables import ChoiceFieldColumn, NetBoxTable, columns

from .models import Equipment, EquipmentFlow, Plateau


class PlateauTable(NetBoxTable):
    name = tables.Column(linkify=True, verbose_name=_('Name'))
    site = tables.Column(linkify=True, verbose_name=_('Establishment'))
    category = ChoiceFieldColumn(verbose_name=_('Category'))
    equipment_count = tables.Column(verbose_name=_('Equipments'))
    tags = columns.TagColumn(url_name='plugins:netbox_biomed:plateau_list')

    class Meta(NetBoxTable.Meta):
        model = Plateau
        fields = (
            'pk', 'id', 'name', 'site', 'category', 'manager',
            'description', 'equipment_count', 'tags',
        )
        default_columns = ('name', 'site', 'category', 'manager', 'equipment_count')


class EquipmentTable(NetBoxTable):
    name = tables.Column(linkify=True, verbose_name=_('Name'))
    role = ChoiceFieldColumn(verbose_name=_('Role'))
    site = tables.Column(linkify=True, verbose_name=_('Establishment'))
    plateau = tables.Column(linkify=True, verbose_name=_('Technical platform'))
    manufacturer = tables.Column(linkify=True, verbose_name=_('Manufacturer'))
    primary_ip = tables.Column(linkify=True, verbose_name=_('IP'))
    vlan = tables.Column(linkify=True, verbose_name=_('VLAN'))
    category = ChoiceFieldColumn(verbose_name=_('Category'))
    status = ChoiceFieldColumn(verbose_name=_('Status'))
    criticality = ChoiceFieldColumn(verbose_name=_('Criticality'))
    device_class = ChoiceFieldColumn(verbose_name=_('Device class'))
    network_exposure = ChoiceFieldColumn(verbose_name=_('Exposure'))
    connection_mode = ChoiceFieldColumn(verbose_name=_('Connection'))
    os_obsolete = columns.BooleanColumn(
        verbose_name=_('OS out of support'), orderable=False,
    )
    remote_maintenance = columns.BooleanColumn(verbose_name=_('Remote maint.'))
    applications = tables.ManyToManyColumn(
        linkify_item=True, verbose_name=_('Applications'),
    )
    tags = columns.TagColumn(url_name='plugins:netbox_biomed:equipment_list')

    class Meta(NetBoxTable.Meta):
        model = Equipment
        fields = (
            'pk', 'id', 'name', 'role', 'site', 'plateau', 'category',
            'manufacturer', 'model', 'serial', 'gmao_id', 'status',
            'criticality', 'device_class', 'primary_ip', 'mac_address',
            'hostname', 'ae_title', 'vlan', 'connection_mode', 'ssid',
            'os', 'end_of_support', 'os_obsolete', 'edr',
            'remote_maintenance', 'network_exposure',
            'applications', 'owner', 'tags',
        )
        default_columns = (
            'name', 'role', 'site', 'plateau', 'manufacturer',
            'primary_ip', 'ae_title', 'status', 'network_exposure',
        )


class EquipmentFlowTable(NetBoxTable):
    name = tables.Column(verbose_name=_('Name'))
    source = tables.Column(linkify=True, verbose_name=_('Source'))
    target = tables.Column(linkify=True, verbose_name=_('Target'))
    protocol = tables.Column(verbose_name=_('Protocol'))
    message_type = tables.Column(verbose_name=_('Message type'))
    encrypted = columns.BooleanColumn(verbose_name=_('Encrypted'))
    status = ChoiceFieldColumn(verbose_name=_('Status'))
    eai = tables.Column(verbose_name=_('EAI'))
    prtg_sensor = tables.URLColumn(verbose_name=_('Monitoring'))
    tags = columns.TagColumn(url_name='plugins:netbox_biomed:equipmentflow_list')
    actions = columns.ActionsColumn()

    id = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = EquipmentFlow
        fields = (
            'pk', 'id', 'name', 'source', 'target', 'protocol',
            'message_type', 'port', 'encrypted', 'status', 'eai',
            'source_endpoint', 'eai_endpoint', 'target_endpoint',
            'prtg_sensor', 'recovery_procedure', 'vendor_contact',
            'description', 'tags',
        )
        default_columns = (
            'id', 'source', 'target', 'protocol', 'message_type',
            'encrypted', 'status', 'eai',
        )
