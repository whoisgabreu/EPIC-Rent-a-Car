from django.urls import path
from django.contrib.auth import views as auth_views
from .views import DashboardView, UploadCSVView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='dashboard/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('upload/', UploadCSVView.as_view(), name='upload_csv'),
]
