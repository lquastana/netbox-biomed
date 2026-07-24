from django.urls import path
from netbox.views.generic import ObjectChangeLogView, ObjectJournalView

from . import models, views, views_carto

urlpatterns = (

    # ── Vues cartographiques ───────────────────────────────────────────────
    path('cyber/', views.CyberDashboardView.as_view(), name='cyber_dashboard'),
    path('carto/', views_carto.BiomedCartoView.as_view(), name='carto'),

    # ── Plateaux techniques ────────────────────────────────────────────────
    path('plateaux/', views.PlateauListView.as_view(), name='plateau_list'),
    path('plateaux/ajouter/', views.PlateauEditView.as_view(), name='plateau_add'),
    path('plateaux/supprimer/', views.PlateauBulkDeleteView.as_view(), name='plateau_bulk_delete'),
    path('plateaux/<int:pk>/', views.PlateauView.as_view(), name='plateau'),
    path('plateaux/<int:pk>/modifier/', views.PlateauEditView.as_view(), name='plateau_edit'),
    path('plateaux/<int:pk>/supprimer/', views.PlateauDeleteView.as_view(), name='plateau_delete'),
    path('plateaux/<int:pk>/journal-modifications/', ObjectChangeLogView.as_view(), name='plateau_changelog', kwargs={'model': models.Plateau}),
    path('plateaux/<int:pk>/journal/', ObjectJournalView.as_view(), name='plateau_journal', kwargs={'model': models.Plateau}),

    # ── Équipements ────────────────────────────────────────────────────────
    path('equipements/', views.EquipmentListView.as_view(), name='equipment_list'),
    path('equipements/ajouter/', views.EquipmentEditView.as_view(), name='equipment_add'),
    path('equipements/supprimer/', views.EquipmentBulkDeleteView.as_view(), name='equipment_bulk_delete'),
    path('equipements/<int:pk>/', views.EquipmentView.as_view(), name='equipment'),
    path('equipements/<int:pk>/modifier/', views.EquipmentEditView.as_view(), name='equipment_edit'),
    path('equipements/<int:pk>/supprimer/', views.EquipmentDeleteView.as_view(), name='equipment_delete'),
    path('equipements/<int:pk>/journal-modifications/', ObjectChangeLogView.as_view(), name='equipment_changelog', kwargs={'model': models.Equipment}),
    path('equipements/<int:pk>/journal/', ObjectJournalView.as_view(), name='equipment_journal', kwargs={'model': models.Equipment}),

    # ── Flux ───────────────────────────────────────────────────────────────
    path('flux/', views.EquipmentFlowListView.as_view(), name='equipmentflow_list'),
    path('flux/ajouter/', views.EquipmentFlowEditView.as_view(), name='equipmentflow_add'),
    path('flux/supprimer/', views.EquipmentFlowBulkDeleteView.as_view(), name='equipmentflow_bulk_delete'),
    path('flux/<int:pk>/', views.EquipmentFlowView.as_view(), name='equipmentflow'),
    path('flux/<int:pk>/modifier/', views.EquipmentFlowEditView.as_view(), name='equipmentflow_edit'),
    path('flux/<int:pk>/supprimer/', views.EquipmentFlowDeleteView.as_view(), name='equipmentflow_delete'),
    path('flux/<int:pk>/journal-modifications/', ObjectChangeLogView.as_view(), name='equipmentflow_changelog', kwargs={'model': models.EquipmentFlow}),
    path('flux/<int:pk>/journal/', ObjectJournalView.as_view(), name='equipmentflow_journal', kwargs={'model': models.EquipmentFlow}),
)
