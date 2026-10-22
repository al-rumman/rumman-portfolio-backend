from rest_framework import serializers

from portfolio.serializers import validate_image

from .models import Category, Comment, ContactMessage, Post, Tag


class CategorySerializer(serializers.ModelSerializer):
    posts_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'posts_count')
        read_only_fields = ('slug',)


class TagSerializer(serializers.ModelSerializer):
    posts_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug', 'posts_count')
        read_only_fields = ('slug',)


class CategoryMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug')


class TagMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


def _likes_count(obj):
    return obj.likes_count if hasattr(obj, 'likes_count') else obj.likes.count()


def _comments_count(obj):
    if hasattr(obj, 'comments_count'):
        return obj.comments_count
    return obj.comments.filter(is_approved=True).count()


class PostListSerializer(serializers.ModelSerializer):
    category = CategoryMiniSerializer(read_only=True)
    tags = TagMiniSerializer(many=True, read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            'id', 'title', 'slug', 'excerpt', 'cover_image', 'category', 'tags',
            'status', 'published_at', 'views_count', 'reading_time',
            'is_featured', 'likes_count', 'comments_count',
        )

    def get_likes_count(self, obj):
        return _likes_count(obj)

    def get_comments_count(self, obj):
        return _comments_count(obj)


class PostDetailSerializer(PostListSerializer):
    author = serializers.CharField(source='author.username', read_only=True)
    is_liked = serializers.SerializerMethodField()
    related_posts = serializers.SerializerMethodField()

    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + (
            'content', 'author', 'is_liked', 'related_posts',
            'created_at', 'updated_at',
        )

    def get_is_liked(self, obj):
        request = self.context.get('request')
        visitor_id = request.headers.get('X-Visitor-Id') if request else None
        if not visitor_id:
            return False
        return obj.likes.filter(visitor_id=visitor_id).exists()

    def get_related_posts(self, obj):
        qs = (
            Post.objects.filter(status=Post.Status.PUBLISHED, category=obj.category)
            .exclude(pk=obj.pk)
            .select_related('category')
            .prefetch_related('tags')[:3]
        )
        return PostListSerializer(qs, many=True, context=self.context).data


class PostWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = (
            'title', 'excerpt', 'content', 'cover_image',
            'category', 'tags', 'status', 'is_featured',
        )

    def validate_title(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError('Title must be at least 5 characters.')
        return value

    def validate_cover_image(self, value):
        if value:
            validate_image(value)
        return value

    def validate(self, attrs):
        inst = self.instance

        def get(name, default=None):
            if name in attrs:
                return attrs[name]
            return getattr(inst, name, default) if inst else default

        if get('status') == Post.Status.PUBLISHED:
            if len((get('content') or '').strip()) < 100:
                raise serializers.ValidationError(
                    {'content': 'A published post needs at least 100 characters of content.'}
                )
            if not get('category'):
                raise serializers.ValidationError(
                    {'category': 'A published post needs a category.'}
                )
        return attrs

    def to_representation(self, instance):
        return PostDetailSerializer(instance, context=self.context).data


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('name', 'email', 'website', 'content', 'parent')

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError('Name must be at least 2 characters.')
        return value

    def validate_content(self, value):
        value = value.strip()
        if not 5 <= len(value) <= 1000:
            raise serializers.ValidationError(
                'Comment must be between 5 and 1000 characters.'
            )
        return value

    def validate_parent(self, value):
        post = self.context['post']
        if value is not None:
            if value.post_id != post.pk:
                raise serializers.ValidationError(
                    'Parent comment belongs to a different post.'
                )
            if value.parent_id is not None:
                raise serializers.ValidationError(
                    'You can only reply to a top-level comment.'
                )
            if not value.is_approved:
                raise serializers.ValidationError(
                    'You cannot reply to a comment that is not approved.'
                )
        return value


class ReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('id', 'name', 'website', 'content', 'created_at')


class CommentPublicSerializer(serializers.ModelSerializer):
    """Public API: email kokhono return hoy na."""
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ('id', 'name', 'website', 'content', 'created_at', 'replies')

    def get_replies(self, obj):
        qs = obj.replies.filter(is_approved=True).order_by('created_at')
        return ReplySerializer(qs, many=True).data


class CommentAdminSerializer(serializers.ModelSerializer):
    post_slug = serializers.CharField(source='post.slug', read_only=True)
    post_title = serializers.CharField(source='post.title', read_only=True)

    class Meta:
        model = Comment
        fields = (
            'id', 'post_slug', 'post_title', 'name', 'email', 'website',
            'content', 'parent', 'is_approved', 'created_at',
        )
        read_only_fields = ('name', 'email', 'website', 'content', 'parent', 'created_at')


class ContactCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ('name', 'email', 'subject', 'message')

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError('Name must be at least 2 characters.')
        return value

    def validate_message(self, value):
        value = value.strip()
        if not 10 <= len(value) <= 2000:
            raise serializers.ValidationError(
                'Message must be between 10 and 2000 characters.'
            )
        return value


class ContactAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = '__all__'
        read_only_fields = ('name', 'email', 'subject', 'message', 'created_at')