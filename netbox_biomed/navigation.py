from django.utils.translation import gettext_lazy as _
from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem

dashboard_items = (
    PluginMenuItem(
        link='plugins:netbox_biomed:carto',
        link_text=_('Biomedical cartography'),
        permissions=['netbox_biomed.view_equipment'],
    ),
    PluginMenuItem(
        link='plugins:netbox_biomed:cyber_dashboard',
        link_text=_('Cyber dashboard'),
        permissions=['netbox_biomed.view_equipment'],
    ),
)

referential_items = (
    PluginMenuItem(
        link='plugins:netbox_biomed:plateau_list',
        link_text=_('Technical platforms'),
        permissions=['netbox_biomed.view_plateau'],
        buttons=(
            PluginMenuButton(
                link='plugins:netbox_biomed:plateau_add',
                title=_('Add'),
                icon_class='mdi mdi-plus-thick',
                permissions=['netbox_biomed.add_plateau'],
            ),
        ),
    ),
    PluginMenuItem(
        link='plugins:netbox_biomed:equipment_list',
        link_text=_('Equipments'),
        permissions=['netbox_biomed.view_equipment'],
        buttons=(
            PluginMenuButton(
                link='plugins:netbox_biomed:equipment_add',
                title=_('Add'),
                icon_class='mdi mdi-plus-thick',
                permissions=['netbox_biomed.add_equipment'],
            ),
        ),
    ),
    PluginMenuItem(
        link='plugins:netbox_biomed:equipmentflow_list',
        link_text=_('Flows'),
        permissions=['netbox_biomed.view_equipmentflow'],
        buttons=(
            PluginMenuButton(
                link='plugins:netbox_biomed:equipmentflow_add',
                title=_('Add'),
                icon_class='mdi mdi-plus-thick',
                permissions=['netbox_biomed.add_equipmentflow'],
            ),
        ),
    ),
)

menu = PluginMenu(
    label='Biomédical',
    groups=(
        (_('Cartography'), dashboard_items),
        (_('Referential'), referential_items),
    ),
    icon_class='mdi mdi-heart-pulse',
)
