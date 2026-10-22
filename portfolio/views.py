from django_filters.rest_framework import CharFilter, DjangoFilterBackend, FilterSet
from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from .models import Education, Experience, Profile, Project, Skill
from .serializers import (
    EducationSerializer,
    ExperienceSerializer,
    ProfileSerializer,
    ProjectSerializer,
    SkillSerializer,
)


class ProfileView(RetrieveUpdateAPIView):
    """GET: sobai. PATCH: shudhu owner. Always single object."""
    serializer_class = ProfileSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        profile = Profile.get_solo()
        if profile is None:
            raise NotFound('Profile has not been created yet.')
        return profile


class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'is_featured']
    search_fields = ['name']
    ordering_fields = ['display_order', 'proficiency']


class ExperienceViewSet(viewsets.ModelViewSet):
    queryset = Experience.objects.all()
    serializer_class = ExperienceSerializer


class EducationViewSet(viewsets.ModelViewSet):
    queryset = Education.objects.all()
    serializer_class = EducationSerializer


class ProjectPagination(PageNumberPagination):
    page_size = 9


class ProjectFilter(FilterSet):
    tech = CharFilter(method='filter_tech')

    class Meta:
        model = Project
        fields = ['category', 'is_featured']

    def filter_tech(self, queryset, name, value):
        if value.isdigit():
            return queryset.filter(tech_stack__id=value).distinct()
        return queryset.filter(tech_stack__name__iexact=value).distinct()


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.prefetch_related('tech_stack')
    serializer_class = ProjectSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = 'slug'
    pagination_class = ProjectPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProjectFilter
    search_fields = ['title', 'summary', 'description']
    ordering_fields = ['completed_date', 'display_order']