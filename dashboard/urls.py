from django.urls import path
from .views import DashboardView, UploadCSVView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('upload/', UploadCSVView.as_view(), name='upload_csv'),
]
