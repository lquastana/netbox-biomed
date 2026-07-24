from netbox.plugins import PluginConfig


class BiomedConfig(PluginConfig):
    name = 'netbox_biomed'
    verbose_name = 'Biomédical'
    description = (
        "Cartographie des équipements biomédicaux connectés : plateaux "
        "techniques, équipements, flux et posture cyber."
    )
    version = '0.5.0'
    author = 'Laurent Quastana'
    base_url = 'biomed'
    min_version = '4.0'


config = BiomedConfig
