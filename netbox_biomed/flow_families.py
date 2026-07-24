"""
Familles de types de flux : regroupement des `message_type` en familles
visuelles pour la cartographie (couleur d'arête, pastilles des nœuds).
"""
from django.utils.translation import gettext_lazy as _

# (clé, libellé, couleur, mots-clés de message_type — insensible à la casse)
FLOW_FAMILIES = [
    ('images', _('Images / DICOM'), '#2563eb',
     ['images', 'dosimétrie', 'dosimetrie']),
    ('worklist', _('Worklist / RDV'), '#0891b2',
     ['worklist', 'rendez-vous']),
    ('identity', _('Identities / movements'), '#8b5cf6',
     ['identités', 'identites', 'identities']),
    ('results', _('Lab results & analyzers'), '#16a34a',
     ['résultats', 'resultats', 'pilotage automates', 'contrôle qualité', 'controle qualite']),
    ('documents', _('Reports / documents'), '#ea580c',
     ['cr / documents', 'compte rendu', 'ordonnance', 'prescription', 'actes']),
    ('signals', _('Vital signs & signals'), '#db2777',
     ['constantes', 'signaux', 'perfusion', 'surveillance température',
      'surveillance temperature', 'appel malade', 'vidéo chirurgicale', 'video chirurgicale']),
    ('telemedicine', _('Telemedicine'), '#0d9488',
     ['téléradiologie', 'teleradiologie', 'télémédecine']),
    ('operations', _('Operations (print, backup…)'), '#64748b',
     ['impression', 'sauvegarde', 'supervision', 'base de données', 'base de donnees',
      'traçabilité', 'tracabilite']),
    ('remote', _('Remote maintenance'), '#dc2626',
     ['télémaintenance', 'telemaintenance']),
    ('referential', _('Referentials & management'), '#d4b106',
     ['référentiel', 'referentiel', 'stocks', 'stock', 'authentification', 'web / api']),
]

FAMILY_COLOR = {key: color for key, _label, color, _kw in FLOW_FAMILIES}
FAMILY_LABEL = {key: label for key, label, _color, _kw in FLOW_FAMILIES}
OTHER_FAMILY = 'other'
OTHER_COLOR = '#9e9e9e'


def family_of(message_type):
    """Famille d'un message_type (repli : 'other')."""
    mt = (message_type or '').strip().lower()
    if not mt:
        return OTHER_FAMILY
    for key, _label, _color, keywords in FLOW_FAMILIES:
        for kw in keywords:
            if kw in mt:
                return key
    return OTHER_FAMILY


def family_color(key):
    return FAMILY_COLOR.get(key, OTHER_COLOR)
