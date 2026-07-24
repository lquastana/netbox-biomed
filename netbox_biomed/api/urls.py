from netbox.api.routers import NetBoxRouter

from . import views

app_name = 'netbox_biomed'

router = NetBoxRouter()
router.register('plateaux', views.PlateauViewSet)
router.register('equipments', views.EquipmentViewSet)
router.register('equipment-flows', views.EquipmentFlowViewSet)

urlpatterns = router.urls
