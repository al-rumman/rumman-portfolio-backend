from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import auth_views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view()),
    path('refresh/', TokenRefreshView.as_view()),
    path('logout/', auth_views.LogoutView.as_view()),
    path('me/', auth_views.MeView.as_view()),
    path('change-password/', auth_views.ChangePasswordView.as_view()),
]