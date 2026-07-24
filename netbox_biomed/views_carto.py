from collections import Counter as collections_counter
from collections import OrderedDict
from urllib.parse import urlencode

from dcim.models import Site
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views import View

from .choices import EquipmentRoleChoices, PlateauCategoryChoices
from .flow_families import (
    FAMILY_LABEL,
    FLOW_FAMILIES,
    family_color,
    family_of,
)
from .models import Equipment, EquipmentFlow, Plateau

# Hex colors for equipment roles (SVG node dots / chips)
ROLE_HEX = {
    EquipmentRoleChoices.MEDICAL_DEVICE: '#16a34a',
    EquipmentRoleChoices.SERVER: '#2563eb',
    EquipmentRoleChoices.WORKSTATION: '#0891b2',
    EquipmentRoleChoices.PRINTER: '#9e9e9e',
    EquipmentRoleChoices.GATEWAY: '#8b5cf6',
    EquipmentRoleChoices.SOFTWARE_INTERFACE: '#f59e0b',
    EquipmentRoleChoices.NETWORK: '#4f46e5',
    EquipmentRoleChoices.REMOTE_ACCESS: '#dc2626',
    EquipmentRoleChoices.MOBILE: '#0d9488',
    EquipmentRoleChoices.OTHER: '#9e9e9e',
}

# Hex colors for plateau categories (tile top border)
CATEGORY_HEX = {
    PlateauCategoryChoices.IMAGING: '#2563eb',
    PlateauCategoryChoices.LABORATORY: '#16a34a',
    PlateauCategoryChoices.POC_LABORATORY: '#0d9488',
    PlateauCategoryChoices.MONITORING: '#0891b2',
    PlateauCategoryChoices.ICU: '#dc2626',
    PlateauCategoryChoices.OPERATING_ROOM: '#8b5cf6',
    PlateauCategoryChoices.OBSTETRICS: '#db2777',
    PlateauCategoryChoices.DIALYSIS: '#4f46e5',
    PlateauCategoryChoices.PHYSIOTHERAPY: '#d4b106',
    PlateauCategoryChoices.PHARMACY: '#ea580c',
    PlateauCategoryChoices.STERILIZATION: '#64748b',
    PlateauCategoryChoices.AI: '#111827',
    PlateauCategoryChoices.OTHER: '#9e9e9e',
}

# ── Per-role node shapes and icons ─────────────────────────────────────────

def _p_rect(x, y, w, h, r=6):
    return (f'M {x + r} {y} H {x + w - r} Q {x + w} {y} {x + w} {y + r} '
            f'V {y + h - r} Q {x + w} {y + h} {x + w - r} {y + h} H {x + r} '
            f'Q {x} {y + h} {x} {y + h - r} V {y + r} Q {x} {y} {x + r} {y} Z')


def _p_pill(x, y, w, h):
    return _p_rect(x, y, w, h, r=h // 2)


def _p_hexagon(x, y, w, h, c=12):
    return (f'M {x + c} {y} H {x + w - c} L {x + w} {y + h // 2} '
            f'L {x + w - c} {y + h} H {x + c} L {x} {y + h // 2} Z')


def _p_parallelogram(x, y, w, h, s=10):
    return f'M {x + s} {y} H {x + w} L {x + w - s} {y + h} H {x} Z'


def _p_arrow(x, y, w, h, c=10):
    """Ribbon arrow: notched on the left, pointed on the right (gateway)."""
    return (f'M {x} {y} H {x + w - c} L {x + w} {y + h // 2} '
            f'L {x + w - c} {y + h} H {x} L {x + c} {y + h // 2} Z')


def _p_shield(x, y, w, h):
    return (f'M {x} {y + 3} Q {x} {y} {x + 6} {y} H {x + w - 6} '
            f'Q {x + w} {y} {x + w} {y + 3} V {y + h - 7} '
            f'L {x + w // 2} {y + h} L {x} {y + h - 7} Z')


SHAPE_BUILDERS = {
    'rect': _p_rect,
    'pill': _p_pill,
    'hexagon': _p_hexagon,
    'parallelogram': _p_parallelogram,
    'arrow': _p_arrow,
    'shield': _p_shield,
}

# Mini stroke icons drawn in a 10x10 box centred on (0, 0)
ROLE_STYLE = {
    EquipmentRoleChoices.MEDICAL_DEVICE: {
        'shape': 'pill', 'icon': 'M -4 0 H 4 M 0 -4 V 4'},
    EquipmentRoleChoices.SERVER: {
        'shape': 'rect', 'icon': 'M -4 -3 H 4 M -4 0 H 4 M -4 3 H 4'},
    EquipmentRoleChoices.WORKSTATION: {
        'shape': 'rect', 'icon': 'M -4 -4 H 4 V 2 H -4 Z M -2 4 H 2'},
    EquipmentRoleChoices.PRINTER: {
        'shape': 'rect', 'icon': 'M -3 -4 H 3 V -1 M -4 -1 H 4 V 3 H -4 Z'},
    EquipmentRoleChoices.GATEWAY: {
        'shape': 'rect', 'double': True,
        'icon': 'M -4 -1.5 H 4 M 2 -3.5 L 4 -1.5 L 2 0.5 M 4 3 H -4 M -2 1 L -4 3 L -2 5'},
    EquipmentRoleChoices.SOFTWARE_INTERFACE: {
        'shape': 'parallelogram',
        'icon': 'M -4 -2 H 3 M 1 -4 L 3 -2 L 1 0 M 4 2 H -3 M -1 0 L -3 2 L -1 4'},
    EquipmentRoleChoices.NETWORK: {
        'shape': 'hexagon', 'icon': 'M 0 -4 V 0 M 0 0 L -4 4 M 0 0 L 4 4'},
    EquipmentRoleChoices.REMOTE_ACCESS: {
        'shape': 'shield',
        'icon': 'M -3 0 H 3 V 4 H -3 Z M -2 0 V -2 A 2 2 0 0 1 2 -2 V 0'},
    EquipmentRoleChoices.MOBILE: {
        'shape': 'pill', 'icon': 'M -2 -4 H 2 V 4 H -2 Z M -1 2.5 H 1'},
    EquipmentRoleChoices.OTHER: {
        'shape': 'rect',
        'icon': 'M 0 0 m -1.5 0 a 1.5 1.5 0 1 0 3 0 a 1.5 1.5 0 1 0 -3 0'},
}


def node_shape(role, x, y, w, h):
    style = ROLE_STYLE.get(role, ROLE_STYLE[EquipmentRoleChoices.OTHER])
    return SHAPE_BUILDERS[style['shape']](x, y, w, h)


def node_shape_inner(role, x, y, w, h):
    """Second tracé (bordure double) pour les rôles marqués 'double'."""
    style = ROLE_STYLE.get(role, ROLE_STYLE[EquipmentRoleChoices.OTHER])
    if not style.get('double'):
        return ''
    return SHAPE_BUILDERS[style['shape']](x + 3, y + 3, w - 6, h - 6)


def node_icon(role):
    style = ROLE_STYLE.get(role, ROLE_STYLE[EquipmentRoleChoices.OTHER])
    return style['icon']


class BiomedCartoView(PermissionRequiredMixin, View):
    """
    Biomedical cartography: technical platform tiles (fleet + alerts) and a
    source → target flow diagram colored by encryption, filterable.
    """
    template_name = 'netbox_biomed/carto.html'
    permission_required = 'netbox_biomed.view_equipment'

    NODE_HEIGHT = 30
    NODE_GAP = 14
    NODE_WIDTH = 250
    SVG_WIDTH = 1100
    LABEL_MAX = 30

    def get(self, request):
        def clean_id(value):
            """N'accepte que des identifiants numériques (évite un 500 sur ?site_id=abc)."""
            value = (value or '').strip()
            return value if value.isdigit() else ''

        site_id = clean_id(request.GET.get('site_id'))
        plateau_id = clean_id(request.GET.get('plateau_id'))
        role = request.GET.get('role') or ''
        protocol = request.GET.get('protocol') or ''
        family = request.GET.get('family') or ''
        q = (request.GET.get('q') or '').strip()
        mode = 'flux' if request.GET.get('view') == 'flux' else 'plateaux'
        base_qs = urlencode({k: v for k, v in {
            'site_id': site_id, 'plateau_id': plateau_id, 'role': role,
            'protocol': protocol, 'family': family, 'q': q,
        }.items() if v})

        # ── Plateau tiles ──────────────────────────────────────────────────
        plateaux = Plateau.objects.restrict(request.user, 'view').select_related('site').annotate(
            equipment_count=Count('equipments', distinct=True),
            dm_count=Count('equipments', distinct=True, filter=Q(
                equipments__role=EquipmentRoleChoices.MEDICAL_DEVICE)),
        ).order_by('site__name', 'name')
        if site_id:
            plateaux = plateaux.filter(site_id=site_id)

        tiles = []
        for plateau in plateaux:
            flow_count = EquipmentFlow.objects.restrict(request.user, 'view').filter(
                Q(source__plateaux=plateau) | Q(target__plateaux=plateau),
            ).distinct().count()
            tiles.append({
                'plateau': plateau,
                'color': CATEGORY_HEX.get(plateau.category, '#9e9e9e'),
                'equipment_count': plateau.equipment_count,
                'dm_count': plateau.dm_count,
                'flow_count': flow_count,
            })

        # ── Flows (filtered) ───────────────────────────────────────────────
        flows = EquipmentFlow.objects.restrict(request.user, 'view').select_related(
            'source', 'target',
        )
        if site_id:
            flows = flows.filter(Q(source__site_id=site_id) | Q(target__site_id=site_id))
        if plateau_id:
            flows = flows.filter(Q(source__plateaux=plateau_id) | Q(target__plateaux=plateau_id)).distinct()
        if role:
            flows = flows.filter(Q(source__role=role) | Q(target__role=role))
        if protocol:
            flows = flows.filter(protocol__iexact=protocol)
        if q:
            flows = flows.filter(
                Q(name__icontains=q)
                | Q(message_type__icontains=q)
                | Q(source__name__icontains=q)
                | Q(target__name__icontains=q)
            )
        flows = list(flows)
        if family:
            flows = [f for f in flows if family_of(f.message_type) == family]

        svg = self._build_diagram(flows) if mode == 'flux' else None
        cards = self._build_cards(request.user, site_id, plateau_id, role, family, q) \
            if mode == 'plateaux' else None

        all_flows = EquipmentFlow.objects.restrict(request.user, 'view')
        protocols = sorted(set(all_flows.values_list('protocol', flat=True)) - {''})
        sites_choices = Site.objects.restrict(request.user, 'view').filter(
            biomed_equipments__isnull=False).distinct().order_by('name')
        plateaux_choices = Plateau.objects.restrict(request.user, 'view').order_by('name')

        legend_roles = [
            {
                'label': choice[1],
                'color': ROLE_HEX[choice[0]],
                'body': node_shape(choice[0], 1, 1, 40, 18),
                'body_inner': node_shape_inner(choice[0], 1, 1, 40, 18),
                'icon': node_icon(choice[0]),
            }
            for choice in EquipmentRoleChoices.CHOICES
        ]
        legend_families = [
            {'key': key, 'label': label, 'color': color}
            for key, label, color, _kw in FLOW_FAMILIES
        ]

        return render(request, self.template_name, {
            'mode': mode,
            'base_qs': base_qs,
            'tiles': tiles,
            'cards': cards,
            'flows': flows,
            'flow_count': len(flows),
            'svg': svg,
            'sites_choices': sites_choices,
            'plateaux_choices': plateaux_choices,
            'role_choices': EquipmentRoleChoices.CHOICES,
            'protocols': protocols,
            'legend_roles': legend_roles,
            'legend_families': legend_families,
            'filter_site_id': site_id,
            'filter_plateau_id': plateau_id,
            'filter_role': role,
            'filter_protocol': protocol,
            'filter_family': family,
            'filter_q': q,
        })

    def _build_cards(self, user, site_id, plateau_id, role, family, q):
        """Vue plateaux compacte : une card par plateau, équipements groupés
        par rôle (en-tête de section icône + libellé + compteur), chaque item
        = point de rôle + nom + pastilles des familles de flux."""
        equipments = Equipment.objects.restrict(user, 'view').select_related(
            'site').prefetch_related('plateaux__site')
        if site_id:
            equipments = equipments.filter(
                Q(site_id=site_id) | Q(plateaux__site_id=site_id)).distinct()
        if plateau_id:
            equipments = equipments.filter(plateaux=plateau_id)
        if role:
            equipments = equipments.filter(role=role)
        if q:
            equipments = equipments.filter(name__icontains=q)
        equipments = list(equipments.order_by('site__name', 'name'))
        # tri par rôle (ordre du ChoiceSet : DM d'abord), puis par nom
        role_rank = {choice[0]: i for i, choice in enumerate(EquipmentRoleChoices.CHOICES)}
        role_label = {choice[0]: choice[1] for choice in EquipmentRoleChoices.CHOICES}
        equipments.sort(key=lambda e: (role_rank.get(e.role, 99), e.name.lower()))

        # familles de flux par équipement (pastilles) + comptage de flux
        flow_edges = list(EquipmentFlow.objects.restrict(user, 'view').values_list(
            'source_id', 'target_id', 'message_type'))
        fam_map = {}
        for src, tgt, mt in flow_edges:
            fam = family_of(mt)
            fam_map.setdefault(src, set()).add(fam)
            fam_map.setdefault(tgt, set()).add(fam)
        if family:
            equipments = [e for e in equipments if family in fam_map.get(e.pk, ())]

        groups = OrderedDict()
        for e in equipments:
            plateaux = list(e.plateaux.all())
            if plateau_id:
                plateaux = [p for p in plateaux if str(p.pk) == plateau_id]
            if plateaux:
                for p in plateaux:
                    groups.setdefault(p, []).append(e)
            else:
                groups.setdefault(None, []).append(e)

        def chip(e):
            name = e.name
            plateau_count = len(e.plateaux.all())
            return {
                'pk': e.pk,
                'label': name,
                'display': name if len(name) <= 32 else name[:31] + '…',
                'color': ROLE_HEX.get(e.role, '#9e9e9e'),
                'shared': plateau_count if plateau_count > 1 else 0,
                'dots': [
                    {'color': family_color(f),
                     'label': str(FAMILY_LABEL.get(f, f))}
                    for f in sorted(fam_map.get(e.pk, ()))
                ],
            }

        cards = []
        # plateaux d'abord, « sans plateau » en dernier
        for plateau, members in sorted(
                groups.items(),
                key=lambda kv: (kv[0] is None,
                                kv[0].site.name.lower() if kv[0] else '',
                                kv[0].name.lower() if kv[0] else '')):
            dm_count = sum(1 for e in members
                           if e.role == EquipmentRoleChoices.MEDICAL_DEVICE)
            shared_count = sum(1 for e in members if len(e.plateaux.all()) > 1)
            member_ids = {e.pk for e in members}
            flow_count = sum(1 for s, t, _ in flow_edges
                             if s in member_ids or t in member_ids)

            # groupes par rôle, dans l'ordre du ChoiceSet
            role_groups = OrderedDict()
            for e in members:
                role_groups.setdefault(e.role, []).append(e)
            groups_out = [
                {
                    'label': role_label.get(r, r),
                    'color': ROLE_HEX.get(r, '#9e9e9e'),
                    'icon': node_icon(r),
                    'count': len(items),
                    'equipments': [chip(e) for e in items],
                }
                for r, items in role_groups.items()
            ]

            cards.append({
                'plateau': plateau,
                'site': plateau.site if plateau else None,
                'color': CATEGORY_HEX.get(plateau.category, '#9e9e9e') if plateau else '#9e9e9e',
                'category': plateau.get_category_display() if plateau and plateau.category else '',
                'count': len(members),
                'dm_count': dm_count,
                'shared_count': shared_count,
                'flow_count': flow_count,
                'groups': groups_out,
            })
        return cards

    def _node(self, equipment, x, y, families=()):
        """Node dict: role-specific shape, tint, icon + flow-type chips."""
        name = equipment.name
        display = name if len(name) <= self.LABEL_MAX else name[:self.LABEL_MAX - 1] + '…'
        color = ROLE_HEX.get(equipment.role, '#9e9e9e')
        # pastilles des familles de flux, alignées au bord droit du nœud
        chips = []
        for i, fam in enumerate(sorted(families)):
            chips.append({
                'cx': x + self.NODE_WIDTH - 10 - i * 11,
                'cy': y + self.NODE_HEIGHT // 2,
                'color': family_color(fam),
            })
        return {
            'pk': equipment.pk,
            'label': name,
            'display': display,
            'color': color,
            'body': node_shape(equipment.role, x, y, self.NODE_WIDTH, self.NODE_HEIGHT),
            'body_inner': node_shape_inner(equipment.role, x, y, self.NODE_WIDTH, self.NODE_HEIGHT),
            'icon': node_icon(equipment.role),
            'icon_x': x + 17,
            'icon_y': y + self.NODE_HEIGHT // 2,
            'text_x': x + 30,
            'text_y': y + self.NODE_HEIGHT // 2 + 4,
            'chips': chips,
            'x': x, 'y': y,
        }

    def _build_diagram(self, flows):
        """Bipartite diagram, edges aggregated by (source, target) and
        colored by encryption; nodes carry a role-colored dot and are
        grouped by technical platform on the source side."""
        if not flows:
            return None

        # Aggregate edges by (source, target); collect flow-type families
        agg = OrderedDict()
        node_families = {}
        for flow in flows:
            key = (flow.source_id, flow.target_id)
            entry = agg.setdefault(key, {
                'source': flow.source, 'target': flow.target,
                'count': 0, 'protocols': set(), 'types': set(),
                'families': collections_counter(),
            })
            entry['count'] += 1
            if flow.protocol:
                entry['protocols'].add(flow.protocol)
            if flow.message_type:
                entry['types'].add(flow.message_type)
            fam = family_of(flow.message_type)
            entry['families'][fam] += 1
            node_families.setdefault(flow.source_id, set()).add(fam)
            node_families.setdefault(flow.target_id, set()).add(fam)

        def display(name):
            if len(name) > self.LABEL_MAX:
                return name[:self.LABEL_MAX - 1] + '…'
            return name

        def plateau_key(equipment):
            first = equipment.plateaux.first()
            return first.name if first else ''

        # Source nodes grouped by plateau, target nodes alphabetical
        sources, targets = OrderedDict(), OrderedDict()
        for entry in agg.values():
            sources.setdefault(entry['source'].pk, entry['source'])
            targets.setdefault(entry['target'].pk, entry['target'])
        source_list = sorted(sources.values(), key=lambda e: (plateau_key(e).lower(), e.name.lower()))
        target_list = sorted(targets.values(), key=lambda e: e.name.lower())

        step = self.NODE_HEIGHT + self.NODE_GAP
        left_x = 10
        right_x = self.SVG_WIDTH - self.NODE_WIDTH - 10
        mid_x = self.SVG_WIDTH // 2

        left_nodes, group_labels = [], []
        y = 20
        previous_plateau = object()
        for equipment in source_list:
            plateau = plateau_key(equipment)
            if plateau != previous_plateau:
                group_labels.append({'label': plateau or _('No platform'), 'y': y + 2})
                y += 18
                previous_plateau = plateau
            left_nodes.append(self._node(
                equipment, left_x, y, node_families.get(equipment.pk, ())))
            y += step
        left_height = y

        right_nodes = []
        y = 20
        for equipment in target_list:
            right_nodes.append(self._node(
                equipment, right_x, y, node_families.get(equipment.pk, ())))
            y += step
        right_height = y

        left_index = {node['pk']: node for node in left_nodes}
        right_index = {node['pk']: node for node in right_nodes}

        edges = []
        for entry in agg.values():
            src = left_index[entry['source'].pk]
            dst = right_index[entry['target'].pk]
            # couleur = famille dominante du lien
            dominant = entry['families'].most_common(1)[0][0]
            types = ', '.join(sorted(entry['types'])) or '?'
            protocols = ', '.join(sorted(entry['protocols']))
            detail = f'{types}' + (f' · {protocols}' if protocols else '')
            edges.append({
                'src_pk': entry['source'].pk,
                'dst_pk': entry['target'].pk,
                'x1': src['x'] + self.NODE_WIDTH,
                'y1': src['y'] + self.NODE_HEIGHT // 2,
                'x2': dst['x'],
                'y2': dst['y'] + self.NODE_HEIGHT // 2,
                'cx': mid_x,
                'color': family_color(dominant),
                'width': min(1.5 + entry['count'] * 0.6, 6),
                'title': f"{entry['source'].name} → {entry['target'].name} "
                         f"({detail}, {entry['count']} flux)",
            })

        return {
            'width': self.SVG_WIDTH,
            'height': max(left_height, right_height) + 20,
            'node_width': self.NODE_WIDTH,
            'node_height': self.NODE_HEIGHT,
            'left_nodes': left_nodes,
            'right_nodes': right_nodes,
            'group_labels': group_labels,
            'edges': edges,
        }
