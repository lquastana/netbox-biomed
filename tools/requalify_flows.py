# -*- coding: utf-8 -*-
"""
Requalifie les flux « Data » (fourre-tout Mercator) en vrais types de
message, par règles (source, cible) fondées sur la connaissance du parc.
Idempotent : ne touche que les flux dont message_type ∈ {Data, DATA, ''}
(ou listés explicitement), rejouable.

Usage :
    NETBOX_URL=… NETBOX_TOKEN=… python requalify_flows.py [--dry-run]
"""
import argparse
import json
import os
import re
import urllib.request

URL = os.environ['NETBOX_URL'].rstrip('/')
TOK = os.environ['NETBOX_TOKEN']


def api(path, method='GET', payload=None):
    req = urllib.request.Request(
        f'{URL}/api{path}', method=method,
        headers={'Authorization': f'Token {TOK}', 'Content-Type': 'application/json'},
        data=json.dumps(payload).encode() if payload is not None else None,
    )
    return json.load(urllib.request.urlopen(req))


def get_all(path):
    out, p = [], f'{path}'
    while p:
        d = api(p)
        out += d['results']
        p = d['next'].replace(f'{URL}/api', '') if d['next'] else None
    return out


def g(v, k='name'):
    return v[k] if isinstance(v, dict) else v


# ── Règles (source_regex, target_regex) → (protocol, message_type) ─────────
# Évaluées dans l'ordre, première qui matche gagne. Casse ignorée.
# Les règles sont chargées depuis `requalify_rules.json` (spécifique au parc,
# NON versionné) ; voir `requalify_rules.example.json` pour le format.
RULES_FILE = os.path.join(os.path.dirname(__file__), 'requalify_rules.json')


def load_rules():
    """Charge les règles [source_regex, target_regex, protocol, message_type]."""
    if not os.path.exists(RULES_FILE):
        raise SystemExit(
            f"Fichier de règles absent : {RULES_FILE} — "
            "copier requalify_rules.example.json et l'adapter au parc.")
    with open(RULES_FILE, encoding='utf-8') as fh:
        return [(s, t, (p, m)) for s, t, p, m in json.load(fh)]


# Repli quand aucune règle de paire ne matche : par protocole / nom existant
def fallback(flow):
    name = (flow['name'] or '').lower()
    protocol = (flow['protocol'] or '').upper()
    if 'worklist' in name:
        return None, 'Worklist'
    if protocol == 'DICOM':
        return None, 'Images'
    if protocol == 'ASTM':
        return None, 'Résultats labo'
    if protocol in ('HTTPS', 'HTPS', 'HTTP'):
        return None, 'Web / API'
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    flows = get_all('/plugins/biomed/equipment-flows/?limit=500')
    targets = [f for f in flows if (f['message_type'] or '').strip().lower() in ('data', '')]
    print(f'Flux à requalifier : {len(targets)} / {len(flows)}')

    compiled = [(re.compile(s, re.I), re.compile(t, re.I), v) for s, t, v in load_rules()]
    counts, remaining = {}, []
    for f in targets:
        src, dst = g(f['source']), g(f['target'])
        match = None
        for rs, rt, (protocol, message_type) in compiled:
            if rs.search(src) and rt.search(dst):
                match = (protocol, message_type)
                break
        if match is None:
            match = fallback(f)
        protocol, message_type = match
        if message_type:
            payload = {'message_type': message_type}
            if protocol and not f['protocol']:
                payload['protocol'] = protocol
            if not args.dry_run:
                api(f"/plugins/biomed/equipment-flows/{f['id']}/", 'PATCH', payload)
            counts[message_type] = counts.get(message_type, 0) + 1
        else:
            remaining.append((src, dst))

    print('\n=== Requalification ===')
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f'{v:4d}  {k}')
    print(f'\nReliquat non requalifié : {len(remaining)}')
    for s, t in remaining[:20]:
        print(f'  - {s} -> {t}')
    if args.dry_run:
        print('\nDRY-RUN : aucune écriture.')


if __name__ == '__main__':
    main()
