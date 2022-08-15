from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet
from rest_framework import status, filters, viewsets, mixins
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from reviews.models import Review, UserCode, Title, Genre, Category, Comment
from .serializers import (
    UserCodeSerializer,
    SignUpSerializer,
    UserSerializer,
    CommentSerializer,
    ReviewSerializer,
    TitleSerializer,
    TitleGetSerializer,
    GenreSerializer,
    CategorySerializer,
)
from .permissions import (
    IsAdmin,
    IsAdminOrReadOnly,
    IsAdminModeratorAuthorOrReadOnly,
)
from .filters import TitleFilter
from .mixins import CreateListDestroyViewSet

User = get_user_model()


class UserViewSet(ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    pagination_class = PageNumberPagination
    page_size = 4
    filter_backends = (filters.SearchFilter,)
    filterset_fields = ('username')
    permission_classes = (IsAdmin,)

    def perform_update(self, serializer):
        user = self.request.user
        if user.is_admin or user.is_moderator:
            return serializer.save()
        return serializer.save(role='user')

    @action(
        methods=['GET', 'PATCH', 'DELETE'],
        detail=False,
        url_path=r'(?P<username>\w+)',
        permission_classes=[IsAdmin, ],
    )
    def username(self, request, username):
        user = get_object_or_404(User, username=username)
        if request.method == 'GET':
            data = UserSerializer(user).data
            return Response(data, status=status.HTTP_200_OK)
        if request.method == 'PATCH':
            serializer = UserSerializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        if request.method == 'DELETE':
            user.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['GET', 'PATCH'],
        detail=False,
        url_path='me',
        permission_classes=[IsAuthenticated, ]
    )
    def me(self, request):
        user = get_object_or_404(User, username=self.request.user)
        if request.method == 'GET':
            data = UserSerializer(user).data
            return Response(data, status=status.HTTP_200_OK)
        serializer = UserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TokenObtainViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = UserCodeSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        if not (request.data.get('username') or request.data.get('email')):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        user = get_object_or_404(
            User,
            username=request.data['username']
        )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh = RefreshToken.for_user(user)
        return Response(
            data={'token': str(refresh.access_token)},
            status=status.HTTP_200_OK
        )


class SignUpViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = SignUpSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, created = User.objects.get_or_create(
            username=serializer.data.get('username'),
            email=serializer.data.get('email')
        )
        confirmation_code = default_token_generator.make_token(user)
        mailing_code = send_mail(
            subject='Код подтверждения от YaMdb',
            message=f'Your confirmation_code is {confirmation_code}',
            from_email=settings.EMAIL_ADMIN,
            recipient_list=[user.email],
            fail_silently=False,
        )
        if UserCode.objects.filter(username=user).exists():
            UserCode.objects.filter(username=user).delete()
        UserCode.objects.create(
            username=user,
            confirmation_code=confirmation_code
        )
        mailing_code
        return Response(data=request.data, status=status.HTTP_200_OK)


class CategoryViewSet(CreateListDestroyViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('^name',)
    permission_classes = (IsAdminOrReadOnly,)
    lookup_field = 'slug'


class GenreViewSet(CreateListDestroyViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('^name', '^slug')
    permission_classes = (IsAdminOrReadOnly,)
    lookup_field = 'slug'


class TitleViewSet(viewsets.ModelViewSet):
    queryset = Title.objects.all()
    serializer_class = TitleSerializer
    search_fields = ('^genre', )
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TitleFilter

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return TitleGetSerializer
        return TitleSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = (IsAdminModeratorAuthorOrReadOnly,)

    def perform_create(self, serializer):
        title_id = self.kwargs.get('title_id')
        title = get_object_or_404(Title, id=title_id)
        serializer.save(author=self.request.user, title=title)

    def get_queryset(self):
        title_id = self.kwargs.get('title_id')
        title = get_object_or_404(Title, id=title_id)
        return title.reviews.all()


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = (IsAdminModeratorAuthorOrReadOnly, )

    def perform_create(self, serializer):
        title_id = self.kwargs.get('title_id')
        title = get_object_or_404(Title, id=title_id)
        review_id = self.kwargs.get('review_id')
        review = get_object_or_404(Review, id=review_id, title=title)
        serializer.save(author=self.request.user, review=review)

    def get_queryset(self):
        title_id = self.kwargs.get('title_id')
        title = get_object_or_404(Title, id=title_id)
        review_id = self.kwargs.get('review_id')
        review = get_object_or_404(Review, id=review_id, title=title)
        return Comment.objects.filter(review=review)
