from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from netbox.models import NetBoxModel

from .choices import (
    ConnectionModeChoices,
    CriticalityChoices,
    DeviceClassChoices,
    EquipmentRoleChoices,
    EquipmentStatusChoices,
    FlowStatusChoices,
    NetworkExposureChoices,
    PlateauCategoryChoices,
)


class Plateau(NetBoxModel):
    """
    Technical platform grouping biomedical equipment of a facility
    (e.g. "Plateau imagerie", "Plateau biologie délocalisée"). Maps the
    Mercator "Bloc applicatif".
    """
    site = models.ForeignKey(
        to='dcim.Site',
        on_delete=models.PROTECT,
        related_name='biomed_plateaux',
        verbose_name=_('Establishment'),
    )
    name = models.CharField(_('Name'), max_length=100)
    category = models.CharField(
        _('Category'), max_length=30,
        choices=PlateauCategoryChoices, blank=True,
    )
    manager = models.CharField(_('Manager'), max_length=100, blank=True)
    description = models.CharField(_('Description'), max_length=200, blank=True)

    clone_fields = ('site', 'category')

    class Meta:
        ordering = ('site', 'name')
        constraints = (
            models.UniqueConstraint(
                fields=('site', 'name'),
                name='%(app_label)s_%(class)s_unique_site_name',
            ),
        )
        verbose_name = _('technical platform')
        verbose_name_plural = _('technical platforms')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:netbox_biomed:plateau', args=[self.pk])

    def get_category_color(self):
        return PlateauCategoryChoices.colors.get(self.category)


class Equipment(NetBoxModel):
    """
    Object of the biomedical referential. Mostly medical devices, but the
    flow graph also involves their supporting infrastructure (servers,
    gateways, workstations…) — the `role` field tells them apart so that
    every flow endpoint lives in a single referential.
    """
    # ── Identity ───────────────────────────────────────────────────────────
    name = models.CharField(_('Name'), max_length=200, unique=True)
    role = models.CharField(
        _('Role'), max_length=30,
        choices=EquipmentRoleChoices,
        default=EquipmentRoleChoices.MEDICAL_DEVICE,
    )
    description = models.CharField(_('Description'), max_length=500, blank=True)

    # ── Classification ─────────────────────────────────────────────────────
    category = models.CharField(
        _('Category'), max_length=30,
        choices=PlateauCategoryChoices, blank=True,
    )
    device_class = models.CharField(
        _('Device class'), max_length=5,
        choices=DeviceClassChoices, blank=True,
        help_text=_('EU MDR / IVDR risk class (medical devices only)'),
    )
    criticality = models.CharField(
        _('Criticality'), max_length=30,
        choices=CriticalityChoices,
        default=CriticalityChoices.STANDARD,
    )
    status = models.CharField(
        _('Status'), max_length=30,
        choices=EquipmentStatusChoices,
        default=EquipmentStatusChoices.IN_SERVICE,
    )

    # ── Attachment ─────────────────────────────────────────────────────────
    site = models.ForeignKey(
        to='dcim.Site',
        on_delete=models.PROTECT,
        related_name='biomed_equipments',
        verbose_name=_('Establishment'),
    )
    plateau = models.ForeignKey(
        to=Plateau,
        on_delete=models.SET_NULL,
        related_name='equipments',
        null=True, blank=True,
        verbose_name=_('Technical platform'),
    )
    location = models.ForeignKey(
        to='dcim.Location',
        on_delete=models.SET_NULL,
        related_name='biomed_equipments',
        null=True, blank=True,
        verbose_name=_('Location (room)'),
    )
    care_unit = models.CharField(_('Care unit'), max_length=100, blank=True)

    # ── Hardware ───────────────────────────────────────────────────────────
    manufacturer = models.ForeignKey(
        to='dcim.Manufacturer',
        on_delete=models.SET_NULL,
        related_name='biomed_equipments',
        null=True, blank=True,
        verbose_name=_('Manufacturer'),
    )
    model = models.CharField(_('Model'), max_length=100, blank=True)
    serial = models.CharField(_('Serial number'), max_length=100, blank=True)
    gmao_id = models.CharField(
        _('CMMS number'), max_length=50, blank=True,
        help_text=_('Equipment number in the biomedical CMMS (source of truth for the fleet)'),
    )
    mercator_id = models.CharField(
        _('Mercator ID'), max_length=200, blank=True,
        help_text=_('Name in the Mercator export (import reconciliation key)'),
    )
    commissioning_date = models.DateField(_('Commissioning date'), null=True, blank=True)

    # ── Network ────────────────────────────────────────────────────────────
    primary_ip = models.ForeignKey(
        to='ipam.IPAddress',
        on_delete=models.SET_NULL,
        related_name='+',
        null=True, blank=True,
        verbose_name=_('Primary IP'),
    )
    mac_address = models.CharField(_('MAC address'), max_length=50, blank=True)
    hostname = models.CharField(_('Hostname'), max_length=100, blank=True)
    ae_title = models.CharField(
        _('AE Title'), max_length=100, blank=True,
        help_text=_('DICOM Application Entity Title'),
    )
    listen_ports = models.CharField(
        _('Listening ports'), max_length=200, blank=True,
        help_text=_('e.g. 104, 2762, 8080'),
    )
    vlan = models.ForeignKey(
        to='ipam.VLAN',
        on_delete=models.SET_NULL,
        related_name='biomed_equipments',
        null=True, blank=True,
        verbose_name=_('VLAN'),
    )
    connection_mode = models.CharField(
        _('Connection mode'), max_length=30,
        choices=ConnectionModeChoices, blank=True,
    )
    ssid = models.CharField(_('Wi-Fi SSID'), max_length=100, blank=True)
    dcim_device = models.ForeignKey(
        to='dcim.Device',
        on_delete=models.SET_NULL,
        related_name='biomed_equipment',
        null=True, blank=True,
        verbose_name=_('DCIM device'),
        help_text=_('Link to the discovered network object, when reconciled'),
    )

    # ── Software / cyber posture ───────────────────────────────────────────
    os = models.CharField(_('Operating system'), max_length=100, blank=True)
    end_of_support = models.DateField(
        _('End of support'), null=True, blank=True,
        help_text=_('Vendor end of software/OS support'),
    )
    edr = models.CharField(
        _('Antivirus / EDR'), max_length=100, blank=True,
        help_text=_('Endpoint protection deployed, or vendor restriction'),
    )
    edr_exclusions = models.CharField(_('AV/EDR exclusions'), max_length=200, blank=True)
    vendor_account = models.CharField(
        _('Vendor account'), max_length=100, blank=True,
        help_text=_('Manufacturer/service account present on the device (audit of default accounts)'),
    )
    vault_ref = models.CharField(
        _('Credentials vault reference'), max_length=200, blank=True,
        help_text=_('Reference of the secret in the password vault — never the secret itself'),
    )
    remote_maintenance = models.BooleanField(
        _('Vendor remote maintenance'), null=True, blank=True,
    )
    remote_maintenance_mode = models.CharField(
        _('Remote maintenance mode'), max_length=100, blank=True,
        help_text=_('e.g. named VPN, vendor box, 4G modem…'),
    )
    network_exposure = models.CharField(
        _('Network exposure'), max_length=30,
        choices=NetworkExposureChoices,
        default=NetworkExposureChoices.UNKNOWN,
    )

    # ── Functional links ───────────────────────────────────────────────────
    applications = models.ManyToManyField(
        to='netbox_it_landscape.Application',
        related_name='biomed_equipments',
        blank=True,
        verbose_name=_('Applications fed'),
        help_text=_('IT-landscape applications this equipment feeds (PACS, LIS…)'),
    )
    owner = models.CharField(_('Owner'), max_length=100, blank=True)
    comments = models.TextField(_('Comments'), blank=True)

    clone_fields = (
        'role', 'category', 'criticality', 'status', 'site', 'plateau',
        'manufacturer', 'connection_mode', 'edr',
    )

    class Meta:
        ordering = ('site', 'name')
        verbose_name = _('biomedical equipment')
        verbose_name_plural = _('biomedical equipments')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:netbox_biomed:equipment', args=[self.pk])

    def get_role_color(self):
        return EquipmentRoleChoices.colors.get(self.role)

    def get_status_color(self):
        return EquipmentStatusChoices.colors.get(self.status)

    def get_criticality_color(self):
        return CriticalityChoices.colors.get(self.criticality)

    def get_network_exposure_color(self):
        return NetworkExposureChoices.colors.get(self.network_exposure)

    def get_category_color(self):
        return PlateauCategoryChoices.colors.get(self.category)

    def get_connection_mode_color(self):
        return ConnectionModeChoices.colors.get(self.connection_mode)

    @property
    def is_medical_device(self):
        return self.role == EquipmentRoleChoices.MEDICAL_DEVICE

    @property
    def os_obsolete(self):
        """True when the vendor support of the embedded software/OS has ended."""
        return bool(self.end_of_support and self.end_of_support < timezone.now().date())

    @property
    def unencrypted_flow_count(self):
        return (
            self.flows_as_source.filter(encrypted=False).count()
            + self.flows_as_target.filter(encrypted=False).count()
        )


class EquipmentFlow(NetBoxModel):
    """
    Flow between two objects of the biomedical referential (DICOM, HL7,
    ASTM…). Mirrors the Mercator interface sheet, including the EAI leg
    (source endpoint → EAI endpoint → target endpoint) and operational
    metadata (PRTG sensor, recovery procedure, vendor contact).
    """
    name = models.CharField(_('Name'), max_length=200, blank=True)
    source = models.ForeignKey(
        to=Equipment,
        on_delete=models.CASCADE,
        related_name='flows_as_source',
        verbose_name=_('Source'),
    )
    target = models.ForeignKey(
        to=Equipment,
        on_delete=models.CASCADE,
        related_name='flows_as_target',
        verbose_name=_('Target'),
    )
    protocol = models.CharField(
        _('Protocol'), max_length=50, blank=True,
        help_text=_('e.g. DICOM, HL7, ASTM, HTTPS, SFTP'),
    )
    message_type = models.CharField(
        _('Message type'), max_length=100, blank=True,
        help_text=_('e.g. Worklist, Identities/movements, Results, Report'),
    )
    port = models.PositiveIntegerField(_('Port'), null=True, blank=True)
    encrypted = models.BooleanField(_('Encrypted'), null=True, blank=True)
    eai = models.CharField(
        _('EAI'), max_length=100, blank=True,
        help_text=_('Integration engine carrying the flow, if any'),
    )
    source_endpoint = models.CharField(
        _('Source endpoint'), max_length=200, blank=True,
        help_text=_('IP:port on the source side'),
    )
    eai_endpoint = models.CharField(
        _('EAI endpoint'), max_length=200, blank=True,
        help_text=_('IP:port on the integration engine, when relayed'),
    )
    target_endpoint = models.CharField(
        _('Target endpoint'), max_length=200, blank=True,
        help_text=_('IP:port on the target side'),
    )
    status = models.CharField(
        _('Status'), max_length=30,
        choices=FlowStatusChoices,
        default=FlowStatusChoices.PRODUCTION,
    )
    prtg_sensor = models.URLField(
        _('Monitoring sensor'), blank=True,
        help_text=_('Link to the PRTG sensor supervising this flow'),
    )
    recovery_procedure = models.BooleanField(
        _('Recovery procedure'), null=True, blank=True,
        help_text=_('A documented recovery procedure exists'),
    )
    vendor_contact = models.CharField(_('Vendor contact'), max_length=200, blank=True)
    description = models.CharField(_('Description'), max_length=500, blank=True)

    clone_fields = ('source', 'target', 'protocol', 'message_type', 'eai', 'status')

    class Meta:
        ordering = ('source', 'target', 'protocol')
        verbose_name = _('equipment flow')
        verbose_name_plural = _('equipment flows')

    def __str__(self):
        label = f'{self.source.name} → {self.target.name}'
        if self.protocol:
            label += f' ({self.protocol})'
        return label

    def get_absolute_url(self):
        return reverse('plugins:netbox_biomed:equipmentflow', args=[self.pk])

    def get_status_color(self):
        return FlowStatusChoices.colors.get(self.status)
