from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register('skills', views.SkillViewSet, basename='skill')
router.register('experiences', views.ExperienceViewSet, basename='experience')
router.register('education', views.EducationViewSet, basename='education')
router.register('projects', views.ProjectViewSet, basename='project')

urlpatterns = [
    path('profile/', views.ProfileView.as_view()),
] + router.urls