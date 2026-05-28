from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from .serializers import (
    IngredientSerializer,
    RecipeCreateUpdateSerializer,
    RecipeSerializer,
    TagSerializer,
)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [DjangoFilterBackend]
    search_fields = ['name']


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeCreateUpdateSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            if self.request.query_params.get('is_favorited') == '1':
                queryset = queryset.filter(favorited_by__user=user)
            if self.request.query_params.get('is_in_shopping_cart') == '1':
                queryset = queryset.filter(in_shopping_cart__user=user)
        return queryset

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        if request.method == 'POST':
            Favorite.objects.get_or_create(user=request.user, recipe=recipe)
            return Response(status=status.HTTP_201_CREATED)
        else:
            Favorite.objects.filter(user=request.user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = self.get_objects()
        if request.method == 'POST':
            ShoppingCart.objects.get_or_create(
                user=request.user, recipe=recipe)
            return Response(status=status.HTTP_201_CREATED)
        else:
            ShoppingCart.objects.filter(
                user=request.user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=[permissions.IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        cart = ShoppingCart.objects.filter(user=user)
        ingredients = {}
        for item in cart:
            for reitem in item.recipe.recipe_ingredients.all():
                name = reitem.ingredient.name
                unit = reitem.ingredient.measurement_unit
                key = (name, unit)
                ingredients[key] = ingredients.get(key, 0) + reitem.amount
        lines = []
        for (name, unit), amount in ingredients.items():
            line = name + " (" + unit + ") - " + str(amount)
            lines.append(line)
        text = '\n'.join(lines)
        response = HttpResponse(text, content_type='text/plain')
        return response
