from django.core.cache import cache
from django.db.models import Count, F, Q
from django.db.models.deletion import ProtectedError
from django_filters.rest_framework import (
    BooleanFilter,
    CharFilter,
    DjangoFilterBackend,
    FilterSet,
)
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from portfolio.permissions import IsOwner

from .models import Category, Comment, ContactMessage, Post, PostLike, Tag
from .serializers import (
    CategorySerializer,
    CommentAdminSerializer,
    CommentCreateSerializer,
    CommentPublicSerializer,
    ContactAdminSerializer,
    ContactCreateSerializer,
    PostDetailSerializer,
    PostListSerializer,
    PostWriteSerializer,
    TagSerializer,
)
from .throttles import CommentThrottle, ContactThrottle, LikeThrottle

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


class CommentPagination(PageNumberPagination):
    page_size = 10


class ContactPagination(PageNumberPagination):
    page_size = 10


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

    def get_throttles(self):
        throttles = super().get_throttles()
        if self.action == 'like':
            throttles.append(LikeThrottle())
        elif self.action == 'comments' and self.request.method == 'POST':
            throttles.append(CommentThrottle())
        return throttles

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

    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def like(self, request, slug=None):
        """Toggle like. X-Visitor-Id header lagbe."""
        post = self.get_object()
        visitor_id = request.headers.get('X-Visitor-Id', '').strip()
        if not visitor_id:
            return Response(
                {'detail': 'X-Visitor-Id header is required.'}, status=400
            )
        if len(visitor_id) > 64:
            return Response({'detail': 'X-Visitor-Id is too long.'}, status=400)

        like, created = PostLike.objects.get_or_create(
            post=post,
            visitor_id=visitor_id,
            defaults={'ip_address': request.META.get('REMOTE_ADDR')},
        )
        if not created:
            like.delete()
        return Response({'liked': created, 'likes_count': post.likes.count()})

    @action(detail=True, methods=['get', 'post'], permission_classes=[AllowAny])
    def comments(self, request, slug=None):
        post = self.get_object()

        if request.method == 'POST':
            serializer = CommentCreateSerializer(
                data=request.data, context={'post': post}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(post=post, is_approved=False)
            return Response(
                {'detail': 'Your comment is awaiting approval.'}, status=201
            )

        qs = post.comments.filter(is_approved=True, parent__isnull=True).order_by(
            '-created_at'
        )
        paginator = CommentPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        data = CommentPublicSerializer(page, many=True).data
        return paginator.get_paginated_response(data)


class CommentFilter(FilterSet):
    is_approved = BooleanFilter()
    post = CharFilter(field_name='post__slug')

    class Meta:
        model = Comment
        fields = []


class CommentViewSet(viewsets.ModelViewSet):
    """Owner-only moderation list."""
    queryset = Comment.objects.select_related('post').order_by(
        'is_approved', '-created_at'
    )
    serializer_class = CommentAdminSerializer
    permission_classes = [IsOwner]
    pagination_class = CommentPagination
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']
    filter_backends = [DjangoFilterBackend]
    filterset_class = CommentFilter


class ContactViewSet(viewsets.ModelViewSet):
    queryset = ContactMessage.objects.all()
    pagination_class = ContactPagination
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_read']

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsOwner()]

    def get_throttles(self):
        throttles = super().get_throttles()
        if self.action == 'create':
            throttles.append(ContactThrottle())
        return throttles

    def get_serializer_class(self):
        if self.action == 'create':
            return ContactCreateSerializer
        return ContactAdminSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'detail': 'Thanks! Your message has been sent.'}, status=201
        )