from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    DashboardView, UploadCSVView,
    AdminPanelView,
    UserListView, UserCreateView, UserUpdateView, UserDeleteView,
    InvestorListView, InvestorCreateView, InvestorUpdateView, InvestorDeleteView,
    VehicleListView, VehicleCreateView, VehicleUpdateView, VehicleDeleteView,
)

urlpatterns = [
    # ── Core ──────────────────────────────────
    path('', DashboardView.as_view(), name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='dashboard/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('upload/', UploadCSVView.as_view(), name='upload_csv'),

    # ── Admin Panel ───────────────────────────
    path('admin-panel/', AdminPanelView.as_view(), name='admin_panel'),

    # Users
    path('admin-panel/users/', UserListView.as_view(), name='admin_user_list'),
    path('admin-panel/users/create/', UserCreateView.as_view(), name='admin_user_create'),
    path('admin-panel/users/<int:pk>/edit/', UserUpdateView.as_view(), name='admin_user_edit'),
    path('admin-panel/users/<int:pk>/delete/', UserDeleteView.as_view(), name='admin_user_delete'),

    # Investors
    path('admin-panel/investors/', InvestorListView.as_view(), name='admin_investor_list'),
    path('admin-panel/investors/create/', InvestorCreateView.as_view(), name='admin_investor_create'),
    path('admin-panel/investors/<int:pk>/edit/', InvestorUpdateView.as_view(), name='admin_investor_edit'),
    path('admin-panel/investors/<int:pk>/delete/', InvestorDeleteView.as_view(), name='admin_investor_delete'),

    # Vehicles
    path('admin-panel/vehicles/', VehicleListView.as_view(), name='admin_vehicle_list'),
    path('admin-panel/vehicles/create/', VehicleCreateView.as_view(), name='admin_vehicle_create'),
    path('admin-panel/vehicles/<int:pk>/edit/', VehicleUpdateView.as_view(), name='admin_vehicle_edit'),
    path('admin-panel/vehicles/<int:pk>/delete/', VehicleDeleteView.as_view(), name='admin_vehicle_delete'),
]
