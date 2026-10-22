from django.core.cache import cache
from django.db.models import Count, F, Q
from django.db.models.deletion import ProtectedError
from django_filters.rest_framework import CharFilter, DjangoFilterBackend, FilterSet
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .models import Category, Post, Tag
from .serializers import (
    CategorySerializer,
    PostDetailSerializer,
    PostListSerializer,
    PostWriteSerializer,
    TagSerializer,
)

VIEW_COOLDOWN = 60 * 30  # ekoi visitor 30 minute e 1 bar-i view count korbe


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return Category.objects.annotate(
            posts_count=Count(
                'posts', filter=Q(posts__status=Post.Status.PUBLISHED), distinct=True
            )
        )

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': 'This category is used by one or more posts and cannot be deleted.'},
                status=400,
            )


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return Tag.objects.annotate(
            posts_count=Count(
                'posts', filter=Q(posts__status=Post.Status.PUBLISHED), distinct=True
            )
        )


class PostPagination(PageNumberPagination):
    page_size = 6


class PostFilter(FilterSet):
    category = CharFilter(field_name='category__slug')
    tag = CharFilter(field_name='tags__slug', distinct=True)

    class Meta:
        model = Post
        fields = ['is_featured']


class PostViewSet(viewsets.ModelViewSet):
    lookup_field = 'slug'
    pagination_class = PostPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PostFilter
    search_fields = ['title', 'excerpt', 'content']
    ordering_fields = ['published_at', 'views_count', 'likes_count', 'title']
    ordering = ['-published_at']

    def get_queryset(self):
        qs = (
            Post.objects.select_related('category', 'author')
            .prefetch_related('tags')
            .annotate(
                likes_count=Count('likes', distinct=True),
                comments_count=Count(
                    'comments', filter=Q(comments__is_approved=True), distinct=True
                ),
            )
        )
        user = self.request.user
        is_owner = user.is_authenticated and user.is_superuser

        # Visitor shudhu PUBLISHED dekhbe, draft kokhono na
        if not is_owner:
            return qs.filter(status=Post.Status.PUBLISHED)

        if self.action == 'list':
            status = self.request.query_params.get('status', '')
            if status.upper() in ('DRAFT', 'PUBLISHED'):
                return qs.filter(status=status.upper())
            if status.lower() == 'all':
                return qs
            return qs.filter(status=Post.Status.PUBLISHED)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return PostListSerializer
        if self.action == 'retrieve':
            return PostDetailSerializer
        return PostWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        self._count_view(request, instance)
        return Response(self.get_serializer(instance).data)

    def _count_view(self, request, post):
        user = request.user
        if user.is_authenticated and user.is_superuser:
            return
        if post.status != Post.Status.PUBLISHED:
            return
        visitor = request.headers.get('X-Visitor-Id') or request.META.get(
            'REMOTE_ADDR', 'unknown'
        )
        key = f'post-view:{post.pk}:{visitor}'
        # cache.add shudhu tokhoni True dey jokhon key ager theke nai
        if cache.add(key, 1, timeout=VIEW_COOLDOWN):
            Post.objects.filter(pk=post.pk).update(views_count=F('views_count') + 1)
            post.refresh_from_db(fields=['views_count'])