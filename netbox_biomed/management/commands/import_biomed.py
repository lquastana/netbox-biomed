"""
Import the biomedical referential from a normalized JSON file (produced by
the local converter `mercator_to_json.py`). Idempotent: objects are resolved
by name / mercator_id and updated in place, so the command can be replayed.

Usage:
    manage.py import_biomed --file /tmp/mercator_biomed.json --default-site "Mon Etablissement" [--dry-run]
"""
import json

from dcim.models import Manufacturer, Site
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from ipam.models import IPAddress, Prefix

from ...models import Equipment, EquipmentFlow, Plateau


class Command(BaseCommand):
    help = "Import plateaux, equipments and flows from a normalized Mercator JSON export."

    def add_arguments(self, parser):
        parser.add_argument('--file', required=True, help='Path to the normalized JSON file')
        parser.add_argument('--default-site', required=True,
                            help='Site name used when an object carries no site')
        parser.add_argument('--dry-run', action='store_true')

    # ── helpers ────────────────────────────────────────────────────────────

    def resolve_site(self, name):
        if not name:
            name = self.default_site_name
        if name in self._site_cache:
            return self._site_cache[name]
        site = Site.objects.filter(name__iexact=name).first()
        if site is None:
            site = self._site_cache.get(self.default_site_name) or \
                Site.objects.filter(name__iexact=self.default_site_name).first()
            if site is None:
                raise CommandError(f"Site introuvable : {name!r} (ni le site par défaut)")
            self.log(f"  ! site {name!r} inconnu → rattaché à {site.name}")
        self._site_cache[name] = site
        return site

    def resolve_ip(self, ip_str):
        """Find (or create) an IPAddress for a bare IP without mask."""
        if not ip_str:
            return None
        existing = IPAddress.objects.filter(address__net_host=ip_str).first()
        if existing:
            return existing
        prefix = (
            Prefix.objects.filter(prefix__net_contains=ip_str)
            .order_by('-prefix__net_mask_length')
            .first()
        )
        mask = prefix.prefix.prefixlen if prefix else 24
        ip = IPAddress(address=f'{ip_str}/{mask}')
        ip.save()
        self.created['ip'] += 1
        return ip

    def resolve_manufacturer(self, name):
        if not name:
            return None
        key = name.strip().lower()
        if key in self._manuf_cache:
            return self._manuf_cache[key]
        manuf = Manufacturer.objects.filter(name__iexact=name.strip()).first()
        if manuf is None:
            from django.utils.text import slugify
            manuf = Manufacturer.objects.create(
                name=name.strip(), slug=slugify(name.strip()),
            )
            self.created['manufacturer'] += 1
        self._manuf_cache[key] = manuf
        return manuf

    def log(self, msg):
        self.stdout.write(msg)

    # ── main ───────────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.default_site_name = options['default_site']
        self._site_cache = {}
        self._manuf_cache = {}
        self.created = {'plateau': 0, 'equipment': 0, 'flow': 0,
                        'ip': 0, 'manufacturer': 0}
        self.updated = {'plateau': 0, 'equipment': 0, 'flow': 0}
        self.skipped = []

        with open(options['file'], encoding='utf-8') as fh:
            data = json.load(fh)

        with transaction.atomic():
            self.import_plateaux(data.get('plateaux', []))
            self.import_equipments(data.get('equipments', []))
            self.import_flows(data.get('flows', []))
            if self.dry_run:
                transaction.set_rollback(True)

        self.log('')
        self.log('=== Bilan ===')
        for key in ('plateau', 'equipment', 'flow'):
            self.log(f'{key:12s} créés {self.created[key]:4d} · mis à jour {self.updated[key]:4d}')
        self.log(f"{'ip':12s} créées {self.created['ip']:4d}")
        self.log(f"{'manufacturer':12s} créés {self.created['manufacturer']:4d}")
        if self.skipped:
            self.log(f'Ignorés : {len(self.skipped)}')
            for reason in self.skipped[:20]:
                self.log(f'  - {reason}')
        if self.dry_run:
            self.log('DRY-RUN : aucune écriture effectuée.')

    def import_plateaux(self, rows):
        self.log(f'— Plateaux : {len(rows)}')
        for row in rows:
            site = self.resolve_site(row.get('site'))
            obj = Plateau.objects.filter(site=site, name=row['name']).first()
            fields = {
                'category': row.get('category', ''),
                'manager': row.get('manager', ''),
                'description': row.get('description', ''),
            }
            if obj is None:
                if not self.dry_run:
                    Plateau.objects.create(site=site, name=row['name'], **fields)
                self.created['plateau'] += 1
            else:
                changed = False
                for attr, value in fields.items():
                    if value and getattr(obj, attr) != value:
                        setattr(obj, attr, value)
                        changed = True
                if changed and not self.dry_run:
                    obj.save()
                    self.updated['plateau'] += 1

    def import_equipments(self, rows):
        self.log(f'— Équipements : {len(rows)}')
        for row in rows:
            site = self.resolve_site(row.get('site'))
            obj = None
            if row.get('mercator_id'):
                obj = Equipment.objects.filter(mercator_id=row['mercator_id']).first()
            if obj is None:
                obj = Equipment.objects.filter(name=row['name']).first()

            # `plateaux` (liste, export NetBox) ou `plateau` (unique, export Mercator)
            names = row.get('plateaux') or ([row['plateau']] if row.get('plateau') else [])
            plateaux = []
            for plateau_name in names:
                plateau = Plateau.objects.filter(name=plateau_name).first()
                if plateau is None:
                    self.skipped.append(
                        f"plateau inconnu {plateau_name!r} pour {row['name']!r}")
                else:
                    plateaux.append(plateau)

            fields = {
                'role': row.get('role', 'medical_device'),
                'description': (row.get('description') or '')[:500],
                'category': row.get('category', ''),
                'device_class': row.get('device_class', ''),
                'criticality': row.get('criticality') or 'standard',
                'status': row.get('status') or 'in_service',
                'site': site,
                'care_unit': (row.get('care_unit') or '')[:100],
                'model': (row.get('model') or '')[:100],
                'serial': (row.get('serial') or '')[:100],
                'gmao_id': row.get('gmao_id', ''),
                'mercator_id': row.get('mercator_id', ''),
                'commissioning_date': row.get('commissioning_date') or None,
                'mac_address': (row.get('mac_address') or '')[:50],
                'hostname': (row.get('hostname') or '')[:100],
                'ae_title': (row.get('ae_title') or '')[:100],
                'listen_ports': (row.get('listen_ports') or '')[:200],
                'connection_mode': row.get('connection_mode', ''),
                'ssid': (row.get('ssid') or '')[:100],
                'os': (row.get('os') or '')[:100],
                'end_of_support': row.get('end_of_support') or None,
                'edr': (row.get('edr') or '')[:100],
                'edr_exclusions': (row.get('edr_exclusions') or '')[:200],
                'vendor_account': (row.get('vendor_account') or '')[:100],
                'vault_ref': (row.get('vault_ref') or '')[:200],
                'remote_maintenance': row.get('remote_maintenance'),
                'remote_maintenance_mode': (row.get('remote_maintenance_mode') or '')[:100],
                'network_exposure': row.get('network_exposure', 'unknown'),
                'owner': (row.get('owner') or '')[:100],
                'comments': row.get('comments', ''),
            }
            manufacturer = self.resolve_manufacturer(row.get('manufacturer'))
            if manufacturer is not None:
                fields['manufacturer'] = manufacturer
            primary_ip = self.resolve_ip(row.get('ip'))
            if primary_ip is not None:
                fields['primary_ip'] = primary_ip

            if obj is None:
                obj = Equipment.objects.create(name=row['name'], **fields)
                obj.plateaux.set(plateaux)
                self.created['equipment'] += 1
            else:
                changed = False
                for attr, value in fields.items():
                    if value in ('', None):
                        continue
                    if getattr(obj, attr) != value:
                        setattr(obj, attr, value)
                        changed = True
                # union : on ajoute les rattachements manquants sans en retirer
                missing = [p for p in plateaux
                           if not obj.plateaux.filter(pk=p.pk).exists()]
                if missing:
                    obj.plateaux.add(*missing)
                    changed = True
                if changed:
                    obj.save()
                    self.updated['equipment'] += 1

    def import_flows(self, rows):
        self.log(f'— Flux : {len(rows)}')
        equipments = {e.name: e for e in Equipment.objects.all()}
        for row in rows:
            source = equipments.get(row['source'])
            target = equipments.get(row['target'])
            if source is None or target is None:
                missing = row['source'] if source is None else row['target']
                self.skipped.append(f"extrémité inconnue {missing!r} (flux {row.get('name', '?')!r})")
                continue

            fields = {
                'name': row.get('name', '')[:200],
                'protocol': row.get('protocol', '')[:50],
                'message_type': row.get('message_type', '')[:100],
                'port': row.get('port'),
                'encrypted': row.get('encrypted'),
                'eai': row.get('eai', '')[:100],
                'source_endpoint': row.get('source_endpoint', '')[:200],
                'eai_endpoint': row.get('eai_endpoint', '')[:200],
                'target_endpoint': row.get('target_endpoint', '')[:200],
                'recovery_procedure': row.get('recovery_procedure'),
                'vendor_contact': row.get('vendor_contact', '')[:200],
                'description': row.get('description', '')[:500],
            }

            obj = EquipmentFlow.objects.filter(
                source=source, target=target,
                protocol=fields['protocol'],
                message_type=fields['message_type'],
                name=fields['name'],
            ).first()
            if obj is None:
                EquipmentFlow.objects.create(source=source, target=target, **fields)
                self.created['flow'] += 1
            else:
                changed = False
                for attr, value in fields.items():
                    if value in ('', None):
                        continue
                    if getattr(obj, attr) != value:
                        setattr(obj, attr, value)
                        changed = True
                if changed:
                    obj.save()
                    self.updated['flow'] += 1
