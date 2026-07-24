from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, Q
from django.utils import timezone
from django.views.generic import TemplateView
from netbox.views import generic

from . import filtersets, forms, tables
from .choices import EquipmentRoleChoices, NetworkExposureChoices
from .models import Equipment, EquipmentFlow, Plateau

#
# Plateaux techniques
#

class PlateauListView(generic.ObjectListView):
    queryset = Plateau.objects.select_related('site').annotate(
        equipment_count=Count('equipments', distinct=True),
    )
    table = tables.PlateauTable
    filterset = filtersets.PlateauFilterSet
    filterset_form = forms.PlateauFilterForm


class PlateauView(generic.ObjectView):
    queryset = Plateau.objects.select_related('site')

    def get_extra_context(self, request, instance):
        equipments = instance.equipments.select_related(
            'site', 'manufacturer', 'primary_ip',
        )
        return {
            'equipment_table': tables.EquipmentTable(equipments, exclude=('plateau',)),
            'equipment_count': equipments.count(),
        }


class PlateauEditView(generic.ObjectEditView):
    queryset = Plateau.objects.all()
    form = forms.PlateauForm


class PlateauDeleteView(generic.ObjectDeleteView):
    queryset = Plateau.objects.all()


class PlateauBulkDeleteView(generic.BulkDeleteView):
    queryset = Plateau.objects.all()
    filterset = filtersets.PlateauFilterSet
    table = tables.PlateauTable


#
# Équipements
#

class EquipmentListView(generic.ObjectListView):
    queryset = Equipment.objects.select_related(
        'site', 'plateau', 'manufacturer', 'primary_ip', 'vlan',
    )
    table = tables.EquipmentTable
    filterset = filtersets.EquipmentFilterSet
    filterset_form = forms.EquipmentFilterForm


class EquipmentView(generic.ObjectView):
    queryset = Equipment.objects.select_related(
        'site', 'plateau', 'location', 'manufacturer',
        'primary_ip', 'vlan', 'dcim_device',
    )

    def get_extra_context(self, request, instance):
        flows_out = instance.flows_as_source.select_related('source', 'target')
        flows_in = instance.flows_as_target.select_related('source', 'target')
        return {
            'flows_out_table': tables.EquipmentFlowTable(flows_out, exclude=('source',)),
            'flows_in_table': tables.EquipmentFlowTable(flows_in, exclude=('target',)),
            'flows_out_count': flows_out.count(),
            'flows_in_count': flows_in.count(),
        }


class EquipmentEditView(generic.ObjectEditView):
    queryset = Equipment.objects.all()
    form = forms.EquipmentForm


class EquipmentDeleteView(generic.ObjectDeleteView):
    queryset = Equipment.objects.all()


class EquipmentBulkDeleteView(generic.BulkDeleteView):
    queryset = Equipment.objects.all()
    filterset = filtersets.EquipmentFilterSet
    table = tables.EquipmentTable


#
# Flux
#

class EquipmentFlowListView(generic.ObjectListView):
    queryset = EquipmentFlow.objects.select_related('source', 'target')
    table = tables.EquipmentFlowTable
    filterset = filtersets.EquipmentFlowFilterSet
    filterset_form = forms.EquipmentFlowFilterForm


class EquipmentFlowView(generic.ObjectView):
    queryset = EquipmentFlow.objects.select_related('source', 'target')


class EquipmentFlowEditView(generic.ObjectEditView):
    queryset = EquipmentFlow.objects.all()
    form = forms.EquipmentFlowForm


class EquipmentFlowDeleteView(generic.ObjectDeleteView):
    queryset = EquipmentFlow.objects.all()


class EquipmentFlowBulkDeleteView(generic.BulkDeleteView):
    queryset = EquipmentFlow.objects.all()
    filterset = filtersets.EquipmentFlowFilterSet
    table = tables.EquipmentFlowTable


#
# Tableau de bord cyber
#

class CyberDashboardView(PermissionRequiredMixin, TemplateView):
    """
    Cyber posture of the biomedical fleet: exposure, out-of-support OS,
    unencrypted flows, unsupervised remote maintenance.
    """
    template_name = 'netbox_biomed/dashboard.html'
    permission_required = 'netbox_biomed.view_equipment'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # object-level permissions : ne montrer que ce que l'utilisateur peut voir
        equipments = Equipment.objects.restrict(self.request.user, 'view')
        devices = equipments.filter(role=EquipmentRoleChoices.MEDICAL_DEVICE)
        flows = EquipmentFlow.objects.restrict(self.request.user, 'view')

        exposed = equipments.filter(network_exposure__in=[
            NetworkExposureChoices.FLAT, NetworkExposureChoices.EXPOSED,
        ])
        os_obsolete = equipments.filter(end_of_support__lt=today)
        no_ip_devices = devices.filter(primary_ip__isnull=True)
        wifi = equipments.exclude(ssid='')
        remote = equipments.filter(remote_maintenance=True)
        vendor_accounts = equipments.exclude(vendor_account='')

        unencrypted = flows.filter(encrypted=False)
        unknown_encryption = flows.filter(encrypted__isnull=True)
        unmonitored = flows.filter(prtg_sensor='')

        per_site = []
        for row in (
            equipments.values('site__id', 'site__name')
            .annotate(
                total=Count('id'),
                dm=Count('id', filter=Q(role=EquipmentRoleChoices.MEDICAL_DEVICE)),
                exposed=Count('id', filter=Q(network_exposure__in=[
                    NetworkExposureChoices.FLAT, NetworkExposureChoices.EXPOSED,
                ])),
                obsolete=Count('id', filter=Q(end_of_support__lt=today)),
            )
            .order_by('site__name')
        ):
            per_site.append(row)

        context.update({
            'total_count': equipments.count(),
            'device_count': devices.count(),
            'flow_count': flows.count(),
            'exposed_count': exposed.count(),
            'os_obsolete_count': os_obsolete.count(),
            'no_ip_device_count': no_ip_devices.count(),
            'wifi_count': wifi.count(),
            'remote_count': remote.count(),
            'vendor_account_count': vendor_accounts.count(),
            'unencrypted_count': unencrypted.count(),
            'unknown_encryption_count': unknown_encryption.count(),
            'unmonitored_count': unmonitored.count(),
            'per_site': per_site,
        })
        return context
