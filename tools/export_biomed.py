# -*- coding: utf-8 -*-
"""
Exporte le référentiel biomédical d'une instance NetBox vers le JSON
normalisé — le même format que celui produit par `mercator_to_json.py`, donc
directement réimportable par `manage.py import_biomed` sur une autre
instance. Permet de partager une cartographie sans repasser par les exports
Mercator.

Usage :
    NETBOX_URL=… NETBOX_TOKEN=… python export_biomed.py --out bundle_biomed.json

⚠️ Le fichier produit contient des données d'infrastructure (IP, comptes
constructeur, plans d'adressage). Il se transmet comme un document interne.
"""
import argparse
import json
import os
import urllib.request

URL = os.environ['NETBOX_URL'].rstrip('/')
TOK = os.environ['NETBOX_TOKEN']

EQUIPMENT_FIELDS = [
    'name', 'role', 'description', 'category', 'device_class', 'criticality',
    'status', 'care_unit', 'model', 'serial', 'gmao_id', 'mercator_id',
    'commissioning_date', 'mac_address', 'hostname', 'ae_title',
    'listen_ports', 'connection_mode', 'ssid', 'os', 'end_of_support',
    'edr', 'edr_exclusions', 'vendor_account', 'vault_ref',
    'remote_maintenance', 'remote_maintenance_mode', 'network_exposure',
    'owner', 'comments',
]
FLOW_FIELDS = [
    'name', 'protocol', 'message_type', 'port', 'encrypted', 'status', 'eai',
    'source_endpoint', 'eai_endpoint', 'target_endpoint',
    'prtg_sensor', 'recovery_procedure', 'vendor_contact', 'description',
]


def get_all(path):
    out, p = [], path
    while p:
        req = urllib.request.Request(
            f'{URL}/api{p}', headers={'Authorization': f'Token {TOK}'})
        d = json.load(urllib.request.urlopen(req))
        out += d['results']
        p = d['next'].replace(f'{URL}/api', '') if d['next'] else None
    return out


def value(v, key='value'):
    """Déplie les champs à choix ({'value': …, 'label': …}) et les FK."""
    if isinstance(v, dict):
        return v.get(key, v.get('name'))
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='bundle_biomed.json')
    args = ap.parse_args()

    plateaux = [
        {
            'name': p['name'],
            'site': value(p['site'], 'name'),
            'category': value(p['category']) or '',
            'manager': p['manager'],
            'description': p['description'],
        }
        for p in get_all('/plugins/biomed/plateaux/?limit=500')
    ]

    equipments = []
    for e in get_all('/plugins/biomed/equipments/?limit=500'):
        row = {f: (value(e[f]) if isinstance(e.get(f), dict) else e.get(f))
               for f in EQUIPMENT_FIELDS}
        row['site'] = value(e['site'], 'name')
        row['plateaux'] = [value(p, 'name') for p in (e.get('plateaux') or [])]
        row['manufacturer'] = value(e['manufacturer'], 'name') if e.get('manufacturer') else ''
        row['ip'] = value(e['primary_ip'], 'address').split('/')[0] if e.get('primary_ip') else ''
        row['applications'] = [value(a, 'name') for a in (e.get('applications') or [])]
        equipments.append({k: v for k, v in row.items() if v not in (None, '', [])})

    flows = []
    for f in get_all('/plugins/biomed/equipment-flows/?limit=500'):
        row = {k: (value(f[k]) if isinstance(f.get(k), dict) else f.get(k))
               for k in FLOW_FIELDS}
        row['source'] = value(f['source'], 'name')
        row['target'] = value(f['target'], 'name')
        flows.append({k: v for k, v in row.items() if v is not None and v != ''})

    payload = {
        'plateaux': plateaux,
        'equipments': equipments,
        'flows': flows,
    }
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    multi = sum(1 for e in equipments if len(e.get('plateaux', [])) > 1)
    print(f'{len(plateaux)} plateaux, {len(equipments)} équipements '
          f'({multi} multi-plateaux), {len(flows)} flux')
    print(f'→ {args.out}')
    print('À importer avec : manage.py import_biomed --file <fichier> --default-site "<Site>"')


if __name__ == '__main__':
    main()
