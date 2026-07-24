# -*- coding: utf-8 -*-
"""
Dérive l'exposition réseau des équipements biomédicaux depuis l'IPAM.

1. Regroupe les équipements par /24 ; crée (get_or_create) les préfixes
   manquants dans l'IPAM avec le rôle « Réseau biomédical » quand le /24 est
   majoritairement biomédical (≥ 70 % des IP IPAM du /24).
2. Dérive `network_exposure` :
   - IP publique                          → exposed
   - 192.9.200.0/24 (plan constructeur)   → isolated
   - préfixe rôle « Réseau biomédical »   → segmented
   - /24 partagé avec d'autres usages     → flat
   - pas d'IP                             → unknown (inchangé)

Idempotent. Usage :
    NETBOX_URL=… NETBOX_TOKEN=… python derive_exposure.py [--dry-run]
"""
import argparse
import collections
import json
import os
import urllib.parse
import urllib.request

URL = os.environ['NETBOX_URL'].rstrip('/')
TOK = os.environ['NETBOX_TOKEN']

BIOMED_ROLE = {'name': 'Réseau biomédical', 'slug': 'reseau-biomedical'}
VENDOR_LEGACY = '192.9.200.'


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


def is_private(ip):
    o = [int(x) for x in ip.split('.')]
    return (o[0] == 10 or (o[0] == 172 and 16 <= o[1] <= 31)
            or (o[0] == 192 and o[1] == 168) or o[0] in (127, 169)
            or ip.startswith(VENDOR_LEGACY))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    equipments = get_all('/plugins/biomed/equipments/?limit=500')
    with_ip = [e for e in equipments if e['primary_ip']]
    print(f'Équipements avec IP : {len(with_ip)} / {len(equipments)}')

    # ── Groupes /24 ────────────────────────────────────────────────────────
    groups = collections.defaultdict(list)
    for e in with_ip:
        ip = g(e['primary_ip'], 'address').split('/')[0]
        net = '.'.join(ip.split('.')[:3]) + '.0/24'
        groups[net].append((e, ip))

    # rôle « Réseau biomédical »
    roles = api(f"/ipam/roles/?slug={BIOMED_ROLE['slug']}")['results']
    if roles:
        role_id = roles[0]['id']
    elif args.dry_run:
        role_id = None
    else:
        role_id = api('/ipam/roles/', 'POST', BIOMED_ROLE)['id']

    prefix_kind = {}   # net → 'public' | 'legacy' | 'biomed' | 'shared'
    for net, members in sorted(groups.items()):
        first_ip = members[0][1]
        if not is_private(first_ip):
            prefix_kind[net] = 'public'
            continue
        if net.startswith(VENDOR_LEGACY):
            prefix_kind[net] = 'legacy'
            continue
        total = api(f"/ipam/ip-addresses/?parent={urllib.parse.quote(net)}&limit=1")['count']
        ratio = len(members) / total if total else 1.0
        kind = 'biomed' if ratio >= 0.7 else 'shared'
        prefix_kind[net] = kind
        print(f'  {net:20s} {len(members):3d} biomed / {total:4d} IP IPAM → {kind}')

        # créer/mettre à jour le préfixe
        existing = api(f"/ipam/prefixes/?prefix={urllib.parse.quote(net)}")['results']
        payload = {
            'prefix': net,
            'status': 'active',
            'description': f'Réseau biomédical ({len(members)} équipements) — déduit de l’import Mercator'
                           if kind == 'biomed' else
                           f'Réseau partagé ({len(members)} équipements biomédicaux) — déduit de l’import Mercator',
        }
        if kind == 'biomed' and role_id:
            payload['role'] = role_id
        if not existing:
            if not args.dry_run:
                api('/ipam/prefixes/', 'POST', payload)
            print(f'    + préfixe créé {net}')
        elif kind == 'biomed' and existing[0]['role'] is None and role_id:
            if not args.dry_run:
                api(f"/ipam/prefixes/{existing[0]['id']}/", 'PATCH', {'role': role_id})
            print(f'    ~ rôle biomédical ajouté à {net}')

    # ── Dérivation de l'exposition ─────────────────────────────────────────
    KIND_TO_EXPOSURE = {
        'public': 'exposed', 'legacy': 'isolated',
        'biomed': 'segmented', 'shared': 'flat',
    }
    changes = collections.Counter()
    for net, members in groups.items():
        exposure = KIND_TO_EXPOSURE[prefix_kind[net]]
        for e, ip in members:
            current = g(e['network_exposure'], 'value') if e['network_exposure'] else 'unknown'
            if current != exposure:
                if not args.dry_run:
                    api(f"/plugins/biomed/equipments/{e['id']}/", 'PATCH',
                        {'network_exposure': exposure})
                changes[f'{current} → {exposure}'] += 1

    print('\n=== Expositions mises à jour ===')
    for k, v in changes.most_common():
        print(f'{v:4d}  {k}')
    if not changes:
        print('aucun changement')
    if args.dry_run:
        print('DRY-RUN : aucune écriture.')


if __name__ == '__main__':
    main()
