# -*- coding: utf-8 -*-
"""
Convertit les 3 exports Mercator (Application / Bloc applicatif / Flux
applicatifs) en un JSON normalisé pour `manage.py import_biomed`, et produit
un rapport qualité.

Les fiches équipement et interface sont des formulaires APLATIS dans la
colonne Description (labels collés aux valeurs, \xa0) → parsing positionnel.

Usage :
    python mercator_to_json.py --dir ~/Desktop --date 20260624 --out mercator_biomed.json --report rapport_qualite.md

⚠️ Les mots de passe présents dans Mercator ne sont JAMAIS exportés — ils
sont seulement comptés dans le rapport qualité.
"""
import argparse
import collections
import json
import os
import re

import pandas as pd

# ── Parsing des formulaires aplatis ────────────────────────────────────────

EQUIP_LABELS = [
    'IP', 'AET', 'HOST NAME', 'Masque', 'Passerelle', 'DNS aux', 'DNS',
    'Port', 'SSID WIFI', 'adresse mac', 'Login', 'Mot de passe', 'VLAN',
    'Numéro Equipement', 'Numéro Équipement', 'Anti Virus exclusions',
    'Anti Virus', 'Source / destinataire', 'Type/Commentaire',
]

FLOW_LABELS = [
    'Environnement', 'EAI', 'Protocole', 'IP port source', 'IP port EAI',
    'IP port cible', 'Sonde PRTG', 'Procédure reprise', 'Contact éditeur',
    'Port',
]


def parse_flat_form(text, labels):
    """Découpe un formulaire aplati en {label: valeur} (positionnel)."""
    d = str(text).replace('\xa0', ' ')
    if d == 'nan':
        return {}
    pos = []
    for lab in labels:
        for m in re.finditer(re.escape(lab), d):
            pos.append((m.start(), m.end(), lab))
    pos.sort()
    kept, last_end = [], -1
    for s, e, lab in pos:
        if s < last_end:        # chevauchement (DNS aux vs DNS, Anti Virus…)
            continue
        kept.append((s, e, lab))
        last_end = e
    out = {}
    for i, (s, e, lab) in enumerate(kept):
        nxt = kept[i + 1][0] if i + 1 < len(kept) else len(d)
        val = d[e:nxt].strip(' : ')
        if val:
            out.setdefault(lab, val)
    return out


IP_RE = re.compile(r'\b(\d{1,3}(?:\.\d{1,3}){3})\b')
MAC_RE = re.compile(r'\b([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}\b')
GMAO_RE = re.compile(r'\b(20\d{7})\b')
PORT_RE = re.compile(r'\b(\d{2,5})\b')


def extract_ip(value):
    m = IP_RE.search(value or '')
    if not m:
        return ''
    ip = m.group(1)
    if all(0 <= int(o) <= 255 for o in ip.split('.')):
        return ip
    return ''


def is_private(ip):
    o = [int(x) for x in ip.split('.')]
    return (
        o[0] == 10
        or (o[0] == 172 and 16 <= o[1] <= 31)
        or (o[0] == 192 and o[1] == 168)
        or o[0] in (127, 169)
        or ip.startswith('192.9.200.')   # plan legacy constructeur interne
    )


# ── Classification des rôles par préfixe de nom ────────────────────────────

ROLE_PREFIXES = {
    'SERV': 'server', 'VM': 'server', 'BASE DE DONNEES': 'server',
    'PC': 'workstation', 'PACSWS': 'workstation', 'STATION': 'workstation',
    'CLIENT': 'workstation', 'CONSOLE': 'workstation',
    'IMPRIMANTE': 'printer', 'GRAVEUR': 'printer',
    'GW': 'gateway', 'INT': 'software_interface',
    'SWITCH': 'network', 'BORNE': 'network',
    'VPN': 'remote_access',
    'IPAD': 'mobile', 'TABLETTE': 'mobile',
}


def classify_role(name):
    n = name.upper().replace('É', 'E')
    for prefix, role in sorted(ROLE_PREFIXES.items(), key=lambda kv: -len(kv[0])):
        if n.startswith(prefix):
            return role
    return 'medical_device'


# ── Fabricants (best effort, mot-clé dans le nom/description) ──────────────

MANUFACTURERS = [
    'Siemens', 'Philips', 'Dräger', 'Draeger', 'Radiometer', 'Abbott',
    'Vepro', 'Canon', 'Samsung', 'Toshiba', 'Fujifilm', 'Fuji', 'Agfa',
    'Mindray', 'Nihon Kohden', 'Medtronic', 'Baxter', 'Fresenius',
    'Steelco', 'Getinge', 'Karl Storz', 'Olympus', 'Pentax', 'Ortho',
    'Werfen', 'Stago', 'Horiba', 'Sysmex', 'Biomérieux', 'Biomerieux',
    'Roche', 'GE Healthcare', 'Vitros', 'Intuitive', 'Gleamer', 'Ambra',
    'Quidel', 'Masimo', 'Stryker',
]
MANUF_ALIASES = {
    'Draeger': 'Dräger', 'Fuji': 'Fujifilm', 'Biomerieux': 'Biomérieux',
    'Vitros': 'Ortho', 'Ortho': 'Ortho Clinical Diagnostics',
}


def guess_manufacturer(name, description):
    hay = f'{name} {description}'.lower()
    for kw in MANUFACTURERS:
        if kw.lower() in hay:
            return MANUF_ALIASES.get(kw, kw)
    return ''


# ── Sites & catégories depuis le nom de bloc/équipement ────────────────────

# Mapping mot-clé → nom de site NetBox, spécifique à l'organisation :
# chargé depuis `site_map.json` (NON versionné, cf. site_map.example.json).
# Format : {"default": "Mon Site", "keywords": {"mot-clé": "Nom du site"}}
_SITE_MAP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site_map.json')
if os.path.exists(_SITE_MAP_FILE):
    with open(_SITE_MAP_FILE, encoding='utf-8') as _fh:
        _SITE_MAP = json.load(_fh)
else:
    _SITE_MAP = {'default': 'Etablissement', 'keywords': {}}


def site_for(text):
    t = (text or '').lower()
    for keyword, site in _SITE_MAP.get('keywords', {}).items():
        if keyword.lower() in t:
            return site
    return _SITE_MAP.get('default', 'Etablissement')


CATEGORY_KEYWORDS = [
    ('imagerie', 'imaging'), ('cardio', 'imaging'),
    ('biologie', 'poc_laboratory'),
    ('réanimation', 'icu'), ('reanimation', 'icu'),
    ('gynéco', 'obstetrics'), ('gyneco', 'obstetrics'),
    ('kiné', 'physiotherapy'), ('kine', 'physiotherapy'),
    ('pharmaceutique', 'pharmacy'), ('pharmacie', 'pharmacy'),
    ('ia', 'ai'), ('gleamer', 'ai'),
]


def category_for(text):
    t = (text or '').lower()
    for kw, cat in CATEGORY_KEYWORDS:
        if kw in t:
            return cat
    return 'other'


# ── Nature des flux : protocole vs type de message ─────────────────────────

PROTOCOL_NATURES = {'DICOM': 'DICOM', 'ASTM': 'ASTM', 'HTPS': 'HTTPS', 'HTTPS': 'HTTPS'}


def split_nature(nature):
    """La colonne Nature mélange protocole et type de message → on sépare."""
    n = (nature or '').strip()
    if not n or n == 'nan':
        return '', ''
    if n in PROTOCOL_NATURES:
        return PROTOCOL_NATURES[n], ''
    if n == 'toto':                      # valeur de test présente dans l'export
        return '', ''
    return '', n                          # Worklist, Identités…, Data (fourre-tout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=os.path.expanduser('~/Desktop'))
    ap.add_argument('--date', default='20260624')
    ap.add_argument('--out', default='mercator_biomed.json')
    ap.add_argument('--report', default='rapport_qualite.md')
    args = ap.parse_args()

    def load(name):
        path = os.path.join(args.dir, f'Mercator - {name} - {args.date}.xlsx')
        df = pd.read_excel(path, header=1)
        df.columns = [str(c).strip() for c in df.columns]
        return df

    app = load('Application')
    bloc = load('Bloc applicatif')
    flux = load('Flux applicatifs')

    quality = collections.defaultdict(list)

    # ── 1. Plateaux (blocs applicatifs) ────────────────────────────────────
    plateaux = []
    for _, row in bloc.iterrows():
        name = str(row['Nom']).strip()
        if not name or name == 'nan':
            continue
        plateaux.append({
            'name': name,
            'site': site_for(name),
            'category': category_for(name),
            'manager': '' if str(row.get('Responsable')) == 'nan' else str(row.get('Responsable')).strip(),
            'description': '' if str(row.get('Description')) == 'nan' else str(row.get('Description')).strip()[:200],
        })

    # ── 2. Équipements (périmètre Biomédical uniquement) ───────────────────
    equipments = []
    password_count = login_count = 0
    for _, row in app.iterrows():
        resp = str(row.get('Responsable', ''))
        if 'Biom' not in resp:
            continue
        name = str(row['Nom']).strip()
        fiche = parse_flat_form(row.get('Description'), EQUIP_LABELS)

        # secrets : comptés, jamais exportés
        if fiche.get('Mot de passe', '').strip():
            password_count += 1
            quality['secrets'].append(name)
        login = fiche.get('Login', '').strip()
        if login:
            login_count += 1

        ip = extract_ip(fiche.get('IP', ''))
        if not ip:
            quality['sans_ip'].append(name)
        mac = ''
        m = MAC_RE.search(fiche.get('adresse mac', '') or '')
        if m:
            mac = m.group(0)

        gmao = ''
        g = GMAO_RE.search(name) or GMAO_RE.search(fiche.get('Numéro Equipement', '') or fiche.get('Numéro Équipement', ''))
        if g:
            gmao = g.group(1)
        else:
            quality['sans_gmao'].append(name)

        aet = fiche.get('AET', '').strip()
        if len(aet) > 30:                 # champ pollué par la valeur suivante
            quality['aet_suspect'].append(f'{name} → {aet[:40]}')
            aet = ''

        ssid = fiche.get('SSID WIFI', '').strip()
        connection_mode = 'wifi' if ssid and ssid.lower() not in ('non', 'nan') else ''

        edr_raw = fiche.get('Anti Virus', '').strip()
        edr = ''
        if edr_raw:
            low = edr_raw.lower()
            if 'sentinel' in low:
                edr = 'SentinelOne'
            elif 'trend' in low:
                edr = 'Trend Micro'
            elif "pas d'antivirus" in low or 'non' == low:
                edr = "Pas d'antivirus possible"
            else:
                edr = edr_raw[:100]

        exposure = 'unknown'
        if ip and not is_private(ip):
            exposure = 'exposed'
            quality['ip_publique'].append(f'{name} → {ip}')

        bloc_name = str(row.get('Bloc applicatif', '')).strip()
        if bloc_name == 'nan':
            bloc_name = ''
            quality['sans_plateau'].append(name)

        ports = fiche.get('Port', '').strip()
        listen_ports = ', '.join(dict.fromkeys(PORT_RE.findall(ports)))[:200] if ports else ''

        vlan_raw = fiche.get('VLAN', '').strip()
        if vlan_raw and not re.fullmatch(r'(VLAN[_ ]?)?\d{1,4}', vlan_raw):
            quality['vlan_sale'].append(f'{name} → {vlan_raw[:40]}')

        type_comment = fiche.get('Type/Commentaire', '').strip()

        equipments.append({
            'name': name,
            'mercator_id': name,
            'role': classify_role(name),
            'site': site_for(bloc_name or name),
            'plateau': bloc_name,
            'category': category_for(bloc_name),
            'gmao_id': gmao,
            'manufacturer': guess_manufacturer(name, type_comment),
            'ip': ip,
            'mac_address': mac,
            'hostname': fiche.get('HOST NAME', '').strip()[:100],
            'ae_title': aet,
            'listen_ports': listen_ports,
            'connection_mode': connection_mode,
            'ssid': ssid[:100] if connection_mode else '',
            'edr': edr,
            'edr_exclusions': fiche.get('Anti Virus exclusions', '').strip()[:200],
            'vendor_account': login[:100],
            'network_exposure': exposure,
            'owner': resp.strip(),
            'comments': type_comment[:2000],
        })

    # ── 3. Flux ────────────────────────────────────────────────────────────
    eq_names = {e['name'] for e in equipments}
    all_names = set(str(n).strip() for n in app['Nom'].tolist())
    flows = []
    infra_endpoints = set()
    for _, row in flux.iterrows():
        source = str(row['Source']).strip()
        target = str(row['Destination']).strip()
        if source == 'nan' or target == 'nan':
            quality['flux_sans_extremite'].append(str(row.get('Nom', '?')))
            continue
        protocol, message_type = split_nature(str(row.get('Nature', '')))
        if str(row.get('Nature', '')).strip() == 'toto':
            quality['nature_invalide'].append(str(row.get('Nom', '?')))
        if message_type == 'Data':
            quality['nature_data'].append(f'{source} → {target}')

        fiche = parse_flat_form(row.get('Description'), FLOW_LABELS)
        desc_raw = str(row.get('Description', ''))
        if desc_raw in ('nan', 'A completer'):
            desc = ''
        else:
            desc = desc_raw[:500]

        if fiche.get('Protocole', '').strip() and not protocol:
            protocol = fiche['Protocole'].strip().split()[0][:50]

        port = None
        pm = re.search(r'Port\s*:?\s*(\d{2,5})', desc_raw)
        if pm:
            port = int(pm.group(1))

        eai = ''
        eai_endpoint = fiche.get('IP port EAI', '').strip()[:200]
        if eai_endpoint:
            eai = 'Cloverleaf' if 'cloverleaf' in eai_endpoint.lower() else 'EAI'

        reprise = fiche.get('Procédure reprise', '').strip().upper()
        recovery = True if reprise.startswith('O') else False if reprise.startswith('N') else None

        chiffre = str(row.get('Chiffrement', '')).strip().lower()
        encrypted = True if chiffre == 'oui' else False if chiffre == 'non' else None

        for endpoint in (source, target):
            if endpoint not in eq_names and endpoint in all_names:
                infra_endpoints.add(endpoint)

        flows.append({
            'name': str(row.get('Nom', '')).strip()[:200],
            'source': source,
            'target': target,
            'protocol': protocol,
            'message_type': message_type[:100],
            'port': port,
            'encrypted': encrypted,
            'eai': eai,
            'source_endpoint': fiche.get('IP port source', '').strip()[:200],
            'eai_endpoint': eai_endpoint,
            'target_endpoint': fiche.get('IP port cible', '').strip()[:200],
            'recovery_procedure': recovery,
            'vendor_contact': fiche.get('Contact éditeur', '').strip()[:200],
            'description': desc,
        })

    # Extrémités de flux hors périmètre biomed (applis DSI…) → créées en
    # équipements role=server pour garder le graphe fermé.
    for _, row in app.iterrows():
        name = str(row['Nom']).strip()
        if name in infra_endpoints and name not in eq_names:
            equipments.append({
                'name': name,
                'mercator_id': name,
                'role': classify_role(name) if classify_role(name) != 'medical_device' else 'server',
                'site': site_for(name),
                'plateau': '',
                'category': '',
                'gmao_id': '',
                'manufacturer': '',
                'ip': '',
                'mac_address': '', 'hostname': '', 'ae_title': '',
                'listen_ports': '', 'connection_mode': '', 'ssid': '',
                'edr': '', 'edr_exclusions': '', 'vendor_account': '',
                'network_exposure': 'unknown',
                'owner': '' if str(row.get('Responsable')) == 'nan' else str(row.get('Responsable')).strip(),
                'comments': 'Extrémité de flux hors périmètre biomédical (référentiel applicatif DSI).',
            })
            eq_names.add(name)

    # ── 4. Rapport qualité ─────────────────────────────────────────────────
    roles = collections.Counter(e['role'] for e in equipments)
    enc = collections.Counter('oui' if f['encrypted'] else 'non' if f['encrypted'] is False else '?' for f in flows)

    lines = [
        '# Rapport qualité — import Mercator biomédical',
        '',
        f"Source : exports Mercator du {args.date}.",
        '',
        '## Volumes',
        f"- Plateaux : **{len(plateaux)}**",
        f"- Équipements : **{len(equipments)}** (dont {len(infra_endpoints)} extrémités hors périmètre biomed ajoutées pour fermer le graphe)",
        '  - ' + ', '.join(f'{k} : {v}' for k, v in roles.most_common()),
        f"- Flux : **{len(flows)}** — chiffrés : {enc.get('oui', 0)}, non chiffrés : {enc.get('non', 0)}, inconnus : {enc.get('?', 0)}",
        '',
        '## ⚠️ Constats de sécurité',
        f"- **{password_count} mots de passe en clair** dans Mercator (NON importés — à purger de Mercator et à mettre dans LockSelf) ; {login_count} comptes constructeur repris dans `vendor_account`.",
        f"- IP publiques : {len(quality['ip_publique'])} — " + '; '.join(quality['ip_publique'][:5]),
        f"- Flux non chiffrés : {enc.get('non', 0)}/{len(flows)}.",
        '',
        '## Complétude',
        f"- Équipements sans IP : {len(quality['sans_ip'])}",
        f"- Équipements sans n° GMAO : {len(quality['sans_gmao'])}",
        f"- Équipements sans plateau : {len(quality['sans_plateau'])}",
        f"- AE Title suspects (champ pollué) : {len(quality['aet_suspect'])}",
        f"- VLAN non normalisables : {len(quality['vlan_sale'])}",
        f"- Flux de nature « Data » à requalifier : {len(quality['nature_data'])}",
        f"- Natures invalides (ex. « toto ») : {len(quality['nature_invalide'])}",
        '',
        '## Détails',
    ]
    for key, title in [
        ('sans_ip', 'Équipements sans IP'),
        ('sans_gmao', 'Équipements sans n° GMAO'),
        ('sans_plateau', 'Équipements sans plateau'),
        ('aet_suspect', 'AE Title suspects'),
        ('vlan_sale', 'VLAN non normalisables'),
        ('ip_publique', 'IP publiques'),
        ('secrets', 'Équipements avec mot de passe en clair dans Mercator'),
    ]:
        items = quality[key]
        if items:
            lines.append(f'\n### {title} ({len(items)})')
            lines += [f'- {i}' for i in items]

    with open(args.report, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')

    payload = {'plateaux': plateaux, 'equipments': equipments, 'flows': flows}
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print(f'{len(plateaux)} plateaux, {len(equipments)} équipements, {len(flows)} flux')
    print(f'→ {args.out}')
    print(f'→ {args.report}')
    print(f'⚠️ {password_count} mots de passe détectés dans Mercator (non exportés)')


if __name__ == '__main__':
    main()
