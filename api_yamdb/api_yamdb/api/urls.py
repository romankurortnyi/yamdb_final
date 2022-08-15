from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import (
    TitleViewSet,
    GenreViewSet,
    CategoryViewSet,
    SignUpViewSet,
    TokenObtainViewSet,
    UserViewSet,
    ReviewViewSet,
    CommentViewSet,
)
from .routers import CustomPostOnlyRouter

app_name = 'api'

auth_router = CustomPostOnlyRouter()
router = SimpleRouter()
auth_router.register('signup', SignUpViewSet, basename='signup')
auth_router.register('token', TokenObtainViewSet, basename='token')
router.register('users', UserViewSet, basename='users')
router.register(r'titles', TitleViewSet, basename='titles')
router.register(r'genres', GenreViewSet, basename='genres')
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'titles/(?P<title_id>\d+)/reviews',
                ReviewViewSet, basename='reviews')
router.register(
    r'titles/(?P<title_id>\d+)/reviews/(?P<review_id>\d+)/comments',
    CommentViewSet, basename='comments'
)
urlpatterns = [
    path('v1/', include(router.urls)),
    path('v1/auth/', include(auth_router.urls)),
]
