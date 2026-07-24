# -*- coding: utf-8 -*-
"""
Détecte et fusionne les équipements en doublon.

Deux équipements sont considérés comme doublons s'ils partagent :
  - le même n° GMAO (clé forte, la GMAO fait foi), ou
  - le même nom normalisé (casse, espaces multiples, accents et ponctuation
    ignorés), ou
  - la même IP primaire ET un nom normalisé très proche.

Le survivant est celui qui porte le plus d'information (IP, AE Title, n° GMAO,
fabricant, plateaux, flux). La fusion :
  - re-pointe les flux entrants/sortants vers le survivant,
  - fait l'UNION des plateaux (d'où l'intérêt du M2M v0.6.0) et des
    applications,
  - complète les champs vides du survivant avec ceux du doublon,
  - supprime le doublon.

Idempotent (relancé, il ne trouve plus rien). Usage :
    NETBOX_URL=… NETBOX_TOKEN=… python merge_duplicates.py [--dry-run]
"""
import argparse
import json
import os
import re
import unicodedata
import urllib.request

URL = os.environ['NETBOX_URL'].rstrip('/')
TOK = os.environ['NETBOX_TOKEN']

# Champs texte complétés depuis le doublon quand ils sont vides chez le survivant
TEXT_FIELDS = [
    'description', 'category', 'device_class', 'care_unit', 'model', 'serial',
    'gmao_id', 'mercator_id', 'mac_address', 'hostname', 'ae_title',
    'listen_ports', 'connection_mode', 'ssid', 'os', 'edr', 'edr_exclusions',
    'vendor_account', 'vault_ref', 'remote_maintenance_mode', 'owner', 'comments',
]
FK_FIELDS = ['manufacturer', 'primary_ip', 'vlan', 'dcim_device', 'location']


def api(path, method='GET', payload=None):
    req = urllib.request.Request(
        f'{URL}/api{path}', method=method,
        headers={'Authorization': f'Token {TOK}', 'Content-Type': 'application/json'},
        data=json.dumps(payload).encode() if payload is not None else None,
    )
    resp = urllib.request.urlopen(req)
    if resp.status == 204:
        return None
    return json.load(resp)


def get_all(path):
    out, p = [], path
    while p:
        d = api(p)
        out += d['results']
        p = d['next'].replace(f'{URL}/api', '') if d['next'] else None
    return out


def g(v, k='name'):
    return v[k] if isinstance(v, dict) else v


def normalize(name):
    """Nom normalisé : sans accents, sans ponctuation, casse et espaces unifiés."""
    s = unicodedata.normalize('NFKD', name or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z0-9]+', ' ', s.lower())
    return ' '.join(s.split())


def richness(e, flow_count):
    """Score d'information : le plus riche survit."""
    score = flow_count * 3
    if e['primary_ip']:
        score += 5
    if e['gmao_id']:
        score += 4
    if e['ae_title']:
        score += 3
    if e['manufacturer']:
        score += 2
    if e['mac_address']:
        score += 2
    score += len(e.get('plateaux') or []) * 2
    score += sum(1 for f in TEXT_FIELDS if e.get(f))
    return score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    equipments = get_all('/plugins/biomed/equipments/?limit=500')
    flows = get_all('/plugins/biomed/equipment-flows/?limit=500')

    flow_count = {}
    for f in flows:
        for end in ('source', 'target'):
            pk = f[end]['id']
            flow_count[pk] = flow_count.get(pk, 0) + 1

    # ── Groupes de doublons ────────────────────────────────────────────────
    groups = {}
    for e in equipments:
        keys = []
        if e['gmao_id']:
            keys.append(('gmao', e['gmao_id'].strip()))
        keys.append(('name', normalize(e['name'])))
        if e['primary_ip']:
            keys.append(('ip', g(e['primary_ip'], 'address').split('/')[0]))
        for key in keys:
            groups.setdefault(key, []).append(e)

    def share_words(members):
        """Les noms ont-ils au moins un mot significatif en commun ?"""
        word_sets = [
            {w for w in normalize(m['name']).split() if len(w) > 2 and not w.isdigit()}
            for m in members
        ]
        common = set.intersection(*word_sets) if word_sets else set()
        return bool(common)

    # Garde-fous : une IP partagée ou un n° GMAO partagé ne suffisent pas si
    # les noms n'ont rien en commun (souvent une erreur de saisie du n° GMAO,
    # ou deux équipements distincts derrière un même NAT/relais).
    merged_pairs, suspects, seen = [], [], set()
    for (kind, value), members in groups.items():
        if len(members) < 2:
            continue
        ids = tuple(sorted(m['id'] for m in members))
        if ids in seen:
            continue
        if kind in ('ip', 'gmao') and not share_words(members):
            suspects.append((kind, value, members))
            seen.add(ids)
            continue
        seen.add(ids)
        merged_pairs.append((kind, value, members))

    if suspects:
        print('⚠️  Groupes SUSPECTS — non fusionnés (noms sans mot commun) :')
        for kind, value, members in suspects:
            print(f'  [{kind} = {value}] ' + ' | '.join(
                f"{m['name']} (#{m['id']})" for m in members))
        print('  → à trancher à la main (souvent : n° GMAO saisi en double).\n')

    # Fusion transitive des groupes qui se chevauchent (union-find) : deux
    # critères différents peuvent désigner les mêmes objets.
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    by_id = {}
    for _kind, _value, members in merged_pairs:
        first = members[0]['id']
        for m in members:
            by_id[m['id']] = m
            union(first, m['id'])

    clusters = {}
    for pk in by_id:
        clusters.setdefault(find(pk), []).append(by_id[pk])
    merged_pairs = [('cluster', f'{len(members)} objets', members)
                    for members in clusters.values() if len(members) > 1]

    if not merged_pairs:
        print('Aucun doublon détecté.')
        return

    print(f'{len(merged_pairs)} groupe(s) de doublons :\n')
    deleted = 0
    for kind, value, members in merged_pairs:
        members = sorted(members, key=lambda m: -richness(m, flow_count.get(m['id'], 0)))
        survivor, losers = members[0], members[1:]
        print(f'[{kind} = {value}]')
        print(f"  survivant : {survivor['name']} (#{survivor['id']}, "
              f"{flow_count.get(survivor['id'], 0)} flux)")

        updates = {}
        plateaux = {p['id'] for p in (survivor.get('plateaux') or [])}
        applications = {a['id'] for a in (survivor.get('applications') or [])}

        for loser in losers:
            print(f"  fusionné  : {loser['name']} (#{loser['id']}, "
                  f"{flow_count.get(loser['id'], 0)} flux)")
            # re-pointage des flux
            for f in flows:
                patch = {}
                if f['source']['id'] == loser['id']:
                    patch['source'] = survivor['id']
                if f['target']['id'] == loser['id']:
                    patch['target'] = survivor['id']
                if patch and not args.dry_run:
                    try:
                        api(f"/plugins/biomed/equipment-flows/{f['id']}/", 'PATCH', patch)
                    except urllib.error.HTTPError as exc:
                        # flux devenu source==target : il perd son sens, on le supprime
                        if exc.code == 400:
                            api(f"/plugins/biomed/equipment-flows/{f['id']}/", 'DELETE')
                        else:
                            raise
            # union des rattachements + complétion des champs vides
            plateaux |= {p['id'] for p in (loser.get('plateaux') or [])}
            applications |= {a['id'] for a in (loser.get('applications') or [])}
            for field in TEXT_FIELDS:
                if not survivor.get(field) and loser.get(field) and field not in updates:
                    updates[field] = loser[field]
            for field in FK_FIELDS:
                if not survivor.get(field) and loser.get(field) and field not in updates:
                    updates[field] = loser[field]['id']

        if plateaux != {p['id'] for p in (survivor.get('plateaux') or [])}:
            updates['plateaux'] = sorted(plateaux)
        if applications != {a['id'] for a in (survivor.get('applications') or [])}:
            updates['applications'] = sorted(applications)

        if updates:
            print(f'  enrichi   : {", ".join(sorted(updates))}')
            if not args.dry_run:
                api(f"/plugins/biomed/equipments/{survivor['id']}/", 'PATCH', updates)
        for loser in losers:
            if not args.dry_run:
                api(f"/plugins/biomed/equipments/{loser['id']}/", 'DELETE')
            deleted += 1
        print()

    print(f'=== Bilan : {deleted} doublon(s) supprimé(s), '
          f'{len(merged_pairs)} groupe(s) fusionné(s) ===')
    if args.dry_run:
        print('DRY-RUN : aucune écriture.')


if __name__ == '__main__':
    main()
