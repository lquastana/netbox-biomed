# netbox-biomed

Plugin NetBox de **cartographie des équipements biomédicaux connectés** :
plateaux techniques, équipements (dispositifs médicaux **et** leur
infrastructure support), flux inter-équipements et **posture cyber**.

*NetBox plugin for mapping connected biomedical equipment: technical
platforms, equipment (medical devices and their supporting infrastructure),
flows and cyber posture.*

## Modèle

- **Plateau** — plateau technique d'un établissement (imagerie, biologie
  délocalisée, réanimation…). FK `dcim.Site`.
- **Equipment** — objet du référentiel biomédical, distingué par un `role`
  (dispositif médical, serveur, passerelle, interface, poste, imprimante…)
  pour que **toutes** les extrémités de flux vivent dans un seul référentiel.
  Fiche réseau (IP → `ipam.IPAddress`, VLAN, AE Title, MAC, Wi-Fi),
  fiche cyber (EDR, exposition, télémaintenance, fin de support, compte
  constructeur + **référence coffre-fort, jamais le secret**), fiche parc
  (n° GMAO, fabricant → `dcim.Manufacturer`, classe RDM/RDIV), lien
  applicatif (M2M `netbox_it_landscape.Application`).
- **EquipmentFlow** — flux entre deux équipements : protocole (DICOM, HL7,
  ASTM…), type de message, chiffrement, extrémités IP:port (source / EAI /
  cible), supervision PRTG, procédure de reprise.

## Tableau de bord cyber

Compteurs cliquables : flux non chiffrés, équipements exposés, OS hors
support, flux non supervisés, télémaintenance constructeur, Wi-Fi — déclinés
par établissement.

## Installation (netbox-docker)

```
# plugin_requirements.txt
/opt/netbox/local-plugins/netbox-biomed
# configuration/plugins.py
PLUGINS = [..., "netbox_biomed"]
```

## Import Mercator

1. Sur le poste : `python tools/mercator_to_json.py --dir <exports> --out mercator_biomed.json --report rapport_qualite.md`
   (les mots de passe présents dans Mercator sont **comptés mais jamais exportés**).
2. Sur l'hôte : `manage.py import_biomed --file mercator_biomed.json [--dry-run]`
   (idempotent : clé `mercator_id` / nom ; IP rattachées à l'IPAM existant).

## i18n

Libellés source en anglais, traduction française fournie
(`locale/fr/LC_MESSAGES/django.po`, compilée via `tools/compile_po.py`).
