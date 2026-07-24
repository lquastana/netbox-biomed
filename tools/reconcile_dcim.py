# -*- coding: utf-8 -*-
"""
Rapprochement des équipements biomédicaux avec l'infrastructure NetBox :

1. `dcim_device` : match par IP primaire partagée, puis hostname == nom de
   device DCIM, puis adresse MAC portée par une interface DCIM.
2. Fabricant par OUI : quand `manufacturer` est vide et qu'une MAC est
   connue, déduit le constructeur depuis l'OUI (table IEEE embarquée pour
   les constructeurs médicaux/IT courants).

Idempotent. Usage :
    NETBOX_URL=… NETBOX_TOKEN=… python reconcile_dcim.py [--dry-run]
"""
import argparse
import json
import os
import re
import urllib.parse
import urllib.request

URL = os.environ['NETBOX_URL'].rstrip('/')
TOK = os.environ['NETBOX_TOKEN']

# OUI → fabricant (extraits IEEE MA-L, constructeurs présents dans le parc)
OUI_VENDORS = {
    '00:09:FB': 'Philips',            # Philips Medical Systems
    '00:1B:FB': 'Philips',
    'B8:D9:CE': 'Samsung',
    '00:16:32': 'Samsung',
    '00:10:8C': 'GE Healthcare',      # GE Medical Systems
    '00:01:FC': 'GE Healthcare',
    '00:0C:B7': 'Dräger',             # Draeger Medical
    '00:26:9C': 'Dräger',
    '00:1A:1B': 'Siemens Healthineers',
    '00:0E:8C': 'Siemens',
    '00:80:F4': 'Canon',
    '00:00:85': 'Canon',
    '00:1E:8F': 'Canon',
    '08:00:37': 'Fujifilm',
    '00:15:99': 'Samsung',
    '00:90:8F': 'Radiometer',         # Audio Codes? — non, garder prudent
    '00:0D:B9': 'PC Engines',
    '00:80:77': 'Brother',
    '00:1B:A9': 'Brother',
    '30:05:5C': 'Brother',
    '00:00:74': 'Ricoh',
    '00:26:73': 'Ricoh',
    '00:17:C8': 'Kyocera',
    '00:21:5A': 'HP',
    '00:23:7D': 'HP',
    '3C:D9:2B': 'HP',
    '98:E7:F4': 'HP',
    'F4:39:09': 'HP',
    '00:14:38': 'HP',
    'B4:99:BA': 'HP',
    '00:15:60': 'HP',
    '00:21:9B': 'Dell',
    '00:24:E8': 'Dell',
    'D4:BE:D9': 'Dell',
    '18:66:DA': 'Dell',
    'F8:B1:56': 'Dell',
    'B8:CA:3A': 'Dell',
    '00:0B:AB': 'Advantech',
    '00:D0:C9': 'Advantech',
    '74:FE:48': 'Advantech',
    '00:90:E8': 'Moxa',               # NPort
    '00:13:95': 'Congatec',
    '00:07:32': 'Aaeon',
    '00:30:64': 'Adlink',
    '00:60:E0': 'Axiom',
    '00:0B:6B': 'Wistron',
    '00:03:1D': 'Cegelec',
    '00:E0:4C': 'Realtek (OEM)',
    '00:07:88': 'Cisco',
    '00:1A:A1': 'Cisco',
}


def api(path, method='GET', payload=None):
    req = urllib.request.Request(
        f'{URL}/api{path}', method=method,
        headers={'Authorization': f'Token {TOK}', 'Content-Type': 'application/json'},
        data=json.dumps(payload).encode() if payload is not None else None,
    )
    return json.load(urllib.request.urlopen(req))


def get_all(path):
    out, p = [], path
    while p:
        d = api(p)
        out += d['results']
        p = d['next'].replace(f'{URL}/api', '') if d['next'] else None
    return out


def g(v, k='name'):
    return v[k] if isinstance(v, dict) else v


def norm_mac(mac):
    m = re.sub(r'[^0-9A-Fa-f]', '', mac or '')
    if len(m) != 12:
        return None
    return ':'.join(m[i:i + 2] for i in range(0, 12, 2)).upper()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    equipments = get_all('/plugins/biomed/equipments/?limit=500')
    devices = get_all('/dcim/devices/?limit=1000')
    dev_by_name = {}
    for d in devices:
        dev_by_name[d['name'].lower()] = d
        dev_by_name[d['name'].split('.')[0].lower()] = d   # nom court des FQDN

    # IP DCIM (assignées à une interface de device)
    dcim_ips = {}
    for ip in get_all('/ipam/ip-addresses/?assigned_to_interface=true&limit=2000'):
        if ip.get('assigned_object') and ip['assigned_object'].get('device'):
            dcim_ips[ip['address'].split('/')[0]] = ip['assigned_object']['device']['id']

    matched, oui_filled, report = 0, 0, []
    for e in equipments:
        updates = {}

        # ── dcim_device ────────────────────────────────────────────────────
        if not e['dcim_device']:
            device_id = None
            how = None
            if e['primary_ip']:
                ip = g(e['primary_ip'], 'address').split('/')[0]
                device_id = dcim_ips.get(ip)
                how = f'IP {ip}'
            if device_id is None and e['hostname']:
                d = dev_by_name.get(e['hostname'].strip().lower())
                if d:
                    device_id, how = d['id'], f"hostname {e['hostname']}"
            if device_id is None and e['mac_address']:
                mac = norm_mac(e['mac_address'])
                if mac:
                    res = api(f'/dcim/interfaces/?mac_address={urllib.parse.quote(mac)}&limit=1')
                    if res['count']:
                        device_id = res['results'][0]['device']['id']
                        how = f'MAC {mac}'
            if device_id:
                updates['dcim_device'] = device_id
                matched += 1
                report.append(f"  {e['name'][:40]:41s} → device #{device_id} ({how})")

        # ── fabricant par OUI ──────────────────────────────────────────────
        if not e['manufacturer'] and e['mac_address']:
            mac = norm_mac(e['mac_address'])
            if mac:
                vendor = OUI_VENDORS.get(mac[:8])
                if vendor:
                    res = api(f'/dcim/manufacturers/?name={urllib.parse.quote(vendor)}')['results']
                    if res:
                        manuf_id = res[0]['id']
                    elif args.dry_run:
                        manuf_id = None
                    else:
                        slug = re.sub(r'[^a-z0-9-]', '-', vendor.lower()).strip('-')
                        manuf_id = api('/dcim/manufacturers/', 'POST',
                                       {'name': vendor, 'slug': slug})['id']
                    if manuf_id or args.dry_run:
                        updates['manufacturer'] = manuf_id
                        oui_filled += 1
                        report.append(f"  {e['name'][:40]:41s} → fabricant {vendor} (OUI {mac[:8]})")

        if updates and not args.dry_run:
            api(f"/plugins/biomed/equipments/{e['id']}/", 'PATCH', updates)

    print('\n'.join(report))
    print(f'\n=== Bilan ===\nDevices DCIM rapprochés : {matched}')
    print(f'Fabricants déduits par OUI : {oui_filled}')
    if args.dry_run:
        print('DRY-RUN : aucune écriture.')


if __name__ == '__main__':
    main()
