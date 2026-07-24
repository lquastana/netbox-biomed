from django.utils.translation import gettext_lazy as _
from utilities.choices import ChoiceSet


class EquipmentRoleChoices(ChoiceSet):
    """
    Nature of the object in the biomedical referential. The Mercator export
    mixes medical devices with their supporting infrastructure (servers,
    workstations, printers, gateways…): a single referential with a role
    keeps the flow graph closed while telling them apart.
    """
    key = 'Equipment.role'

    MEDICAL_DEVICE = 'medical_device'
    SERVER = 'server'
    WORKSTATION = 'workstation'
    PRINTER = 'printer'
    GATEWAY = 'gateway'
    SOFTWARE_INTERFACE = 'software_interface'
    NETWORK = 'network'
    REMOTE_ACCESS = 'remote_access'
    MOBILE = 'mobile'
    OTHER = 'other'

    CHOICES = [
        (MEDICAL_DEVICE, _('Medical device'), 'green'),
        (SERVER, _('Server / VM'), 'blue'),
        (WORKSTATION, _('Workstation / console'), 'cyan'),
        (PRINTER, _('Printer / burner'), 'gray'),
        (GATEWAY, _('Gateway / middleware'), 'purple'),
        (SOFTWARE_INTERFACE, _('Software interface'), 'orange'),
        (NETWORK, _('Network equipment'), 'indigo'),
        (REMOTE_ACCESS, _('Remote access (VPN)'), 'red'),
        (MOBILE, _('Mobile / tablet'), 'teal'),
        (OTHER, _('Other'), 'gray'),
    ]


class PlateauCategoryChoices(ChoiceSet):
    key = 'Plateau.category'

    IMAGING = 'imaging'
    LABORATORY = 'laboratory'
    POC_LABORATORY = 'poc_laboratory'
    MONITORING = 'monitoring'
    ICU = 'icu'
    OPERATING_ROOM = 'operating_room'
    OBSTETRICS = 'obstetrics'
    DIALYSIS = 'dialysis'
    PHYSIOTHERAPY = 'physiotherapy'
    PHARMACY = 'pharmacy'
    STERILIZATION = 'sterilization'
    AI = 'ai'
    OTHER = 'other'

    CHOICES = [
        (IMAGING, _('Imaging'), 'blue'),
        (LABORATORY, _('Laboratory'), 'green'),
        (POC_LABORATORY, _('Point-of-care testing'), 'teal'),
        (MONITORING, _('Patient monitoring'), 'cyan'),
        (ICU, _('Intensive care'), 'red'),
        (OPERATING_ROOM, _('Operating room'), 'purple'),
        (OBSTETRICS, _('Obstetrics'), 'pink'),
        (DIALYSIS, _('Dialysis'), 'indigo'),
        (PHYSIOTHERAPY, _('Physiotherapy'), 'yellow'),
        (PHARMACY, _('Pharmacy'), 'orange'),
        (STERILIZATION, _('Sterilization'), 'gray'),
        (AI, _('Artificial intelligence'), 'black'),
        (OTHER, _('Other'), 'gray'),
    ]


class EquipmentStatusChoices(ChoiceSet):
    key = 'Equipment.status'

    IN_SERVICE = 'in_service'
    MAINTENANCE = 'maintenance'
    OUT_OF_SERVICE = 'out_of_service'
    DECOMMISSIONED = 'decommissioned'
    PROJECT = 'project'

    CHOICES = [
        (IN_SERVICE, _('In service'), 'green'),
        (MAINTENANCE, _('Under maintenance'), 'orange'),
        (OUT_OF_SERVICE, _('Out of service'), 'gray'),
        (DECOMMISSIONED, _('Decommissioned'), 'red'),
        (PROJECT, _('Project'), 'cyan'),
    ]


class DeviceClassChoices(ChoiceSet):
    """EU MDR 2017/745 (I → III) and IVDR 2017/746 (A → D) risk classes."""
    key = 'Equipment.device_class'

    CLASS_I = 'I'
    CLASS_IIA = 'IIa'
    CLASS_IIB = 'IIb'
    CLASS_III = 'III'
    IVD_A = 'A'
    IVD_B = 'B'
    IVD_C = 'C'
    IVD_D = 'D'

    CHOICES = [
        (CLASS_I, _('Class I (MDR)'), 'gray'),
        (CLASS_IIA, _('Class IIa (MDR)'), 'blue'),
        (CLASS_IIB, _('Class IIb (MDR)'), 'orange'),
        (CLASS_III, _('Class III (MDR)'), 'red'),
        (IVD_A, _('Class A (IVDR)'), 'gray'),
        (IVD_B, _('Class B (IVDR)'), 'blue'),
        (IVD_C, _('Class C (IVDR)'), 'orange'),
        (IVD_D, _('Class D (IVDR)'), 'red'),
    ]


class CriticalityChoices(ChoiceSet):
    key = 'Equipment.criticality'

    VITAL = 'vital'
    IMPORTANT = 'important'
    STANDARD = 'standard'

    CHOICES = [
        (VITAL, _('Vital'), 'red'),
        (IMPORTANT, _('Important'), 'orange'),
        (STANDARD, _('Standard'), 'gray'),
    ]


class NetworkExposureChoices(ChoiceSet):
    key = 'Equipment.network_exposure'

    ISOLATED = 'isolated'
    SEGMENTED = 'segmented'
    FLAT = 'flat'
    EXPOSED = 'exposed'
    UNKNOWN = 'unknown'

    CHOICES = [
        (ISOLATED, _('Isolated (closed network)'), 'green'),
        (SEGMENTED, _('Segmented (dedicated VLAN)'), 'blue'),
        (FLAT, _('Flat network'), 'orange'),
        (EXPOSED, _('Exposed (Internet / public IP)'), 'red'),
        (UNKNOWN, _('Unknown'), 'gray'),
    ]


class ConnectionModeChoices(ChoiceSet):
    key = 'Equipment.connection_mode'

    WIRED = 'wired'
    WIFI = 'wifi'
    WIRED_WIFI = 'wired_wifi'
    OFFLINE = 'offline'

    CHOICES = [
        (WIRED, _('Wired'), 'blue'),
        (WIFI, _('Wi-Fi'), 'orange'),
        (WIRED_WIFI, _('Wired + Wi-Fi'), 'purple'),
        (OFFLINE, _('Not connected'), 'gray'),
    ]


class FlowStatusChoices(ChoiceSet):
    key = 'EquipmentFlow.status'

    PRODUCTION = 'production'
    TEST = 'test'
    PROJECT = 'project'
    INACTIVE = 'inactive'

    CHOICES = [
        (PRODUCTION, _('Production'), 'green'),
        (TEST, _('Test / staging'), 'cyan'),
        (PROJECT, _('Project'), 'gray'),
        (INACTIVE, _('Inactive'), 'red'),
    ]
