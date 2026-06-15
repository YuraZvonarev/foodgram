from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from django.urls import reverse
from django.db.models import Sum
from djoser.serializers import SetPasswordSerializer
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from users.models import Subscription

from .serializers import (
    AvatarSerializer,
    FavoriteSerializer,
    IngredientSerializer,
    RecipeCreateUpdateSerializer,
    RecipeSerializer,
    ShoppingCartSerializer,
    SubscriptionCreateSerializer,
    SubscriptionSerializer,
    TagSerializer,
    UserCreateSerializer,
    UserSerializer,
)

User = get_user_model()


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    search_fields = ("name",)


class RecipeViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    search_fields = ("name",)

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return RecipeCreateUpdateSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        queryset = Recipe.objects.all()
        user = self.request.user
        if user.is_authenticated:
            if self.request.query_params.get("is_favorited") == "1":
                queryset = queryset.filter(favorited_by__user=user)
            if self.request.query_params.get("is_in_shopping_cart") == "1":
                queryset = queryset.filter(in_shopping_cart__user=user)
        return queryset

    @action(detail=True, methods=("get",), url_path="get-link")
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_url = request.build_absolute_uri(
            reverse("recipe-get-link", args=[recipe.id])
        )
        return Response({"short-link": short_url})

    @action(
        detail=True,
        methods=("post", "delete"),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        if request.method == "POST":
            serializer = FavoriteSerializer(
                data={"recipe_id": recipe.id}, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        Favorite.objects.filter(user=request.user, recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=("post", "delete"),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        if request.method == "POST":
            serializer = ShoppingCartSerializer(
                data={"recipe_id": recipe.id}, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        ShoppingCart.objects.filter(user=request.user, recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=("get",),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def download_shopping_cart(self, request):
        user = request.user
        data = (
            ShoppingCart.objects.filter(user=user)
            .values(
                "recipe__recipe_ingredients__ingredient__name",
                "recipe__recipe_ingredients__ingredient__measurement_unit",
            )
            .annotate(total=Sum("recipe__recipe_ingredients__amount"))
            .distinct()
        )
        lines = [
            f"{item['recipe__recipe_ingredients__ingredient__name']} ({item['recipe__recipe_ingredients__ingredient__measurement_unit']}) - {item['total']}"
            for item in data
            if item["recipe__recipe_ingredients__ingredient__name"]
            and item["recipe__recipe_ingredients__ingredient__measurement_unit"]
        ]
        return HttpResponse("\n".join(lines), content_type="text/plain")


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    http_method_names = ("get", "post", "delete", "head", "options", "put")

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    @action(
        detail=False,
        methods=("get",),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def subscriptions(self, request):
        subs = Subscription.objects.filter(user=request.user)
        page = self.paginate_queryset(subs)
        if page:
            serializer = SubscriptionSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = SubscriptionSerializer(
            subs, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(
        detail=True,
        methods=("post", "delete"),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def subscribe(self, request, pk=None):
        author = self.get_object()
        if request.method == "POST":
            serializer = SubscriptionCreateSerializer(
                data={"user": request.user.id, "author": author.id},
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            subscription = serializer.save()
            output_serializer = SubscriptionSerializer(
                subscription, context={"request": request}
            )
            return Response(
                output_serializer.data,
                status=status.HTTP_201_CREATED)
        request.user.follower.filter(author=author).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def create(self, request, *args, **kwargs):
        serializer = UserCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=("get",),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=("post",),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def set_password(self, request):
        serializer = SetPasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=("put", "delete"),
        permission_classes=(permissions.IsAuthenticated,),
        url_path="me/avatar",
    )
    def avatar(self, request):
        user = request.user
        if request.method == "PUT":
            serializer = AvatarSerializer(
                user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)
