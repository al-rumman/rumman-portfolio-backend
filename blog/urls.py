from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register('categories', views.CategoryViewSet, basename='category')
router.register('tags', views.TagViewSet, basename='tag')
router.register('posts', views.PostViewSet, basename='post')
router.register('comments', views.CommentViewSet, basename='comment')
router.register('contact', views.ContactViewSet, basename='contact')

urlpatterns = router.urls