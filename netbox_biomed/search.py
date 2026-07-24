from netbox.search import SearchIndex, register_search

from .models import Equipment, EquipmentFlow, Plateau


@register_search
class PlateauIndex(SearchIndex):
    model = Plateau
    fields = (
        ('name', 100),
        ('description', 500),
        ('manager', 300),
    )
    display_attrs = ('site', 'category', 'manager')


@register_search
class EquipmentIndex(SearchIndex):
    model = Equipment
    fields = (
        ('name', 100),
        ('gmao_id', 60),
        ('serial', 60),
        ('ae_title', 100),
        ('hostname', 100),
        ('mac_address', 200),
        ('model', 200),
        ('description', 500),
    )
    display_attrs = ('role', 'site', 'plateau', 'manufacturer', 'status')


@register_search
class EquipmentFlowIndex(SearchIndex):
    model = EquipmentFlow
    fields = (
        ('name', 100),
        ('protocol', 200),
        ('message_type', 200),
        ('eai', 300),
        ('description', 500),
    )
    display_attrs = ('protocol', 'message_type', 'encrypted')
