import base64
import uuid

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)
from users.models import Subscription

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')
    amount = serializers.IntegerField(min_value=1)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeMinfieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class UserCreateSerializer(UserCreateSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'password')


class UserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed')

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return user.following.filter(author=obj).exists()
        return False


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients', many=True, read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.favorited_by.filter(user=user).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.in_shopping_cart.filter(user=request.user).exists()
        return False


class IngredientItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1)

    def validate_id(self, value):
        if not Ingredient.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                'Ингредиент с таким id не найден')
        return value


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True)
    ingredients = IngredientItemSerializer(many=True, write_only=True)
    image = serializers.CharField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time')

    def validate(self, data):
        if data['cooking_time'] <= 0:
            raise serializers.ValidationError(
                {'cooking_time': 'Время приготовления должно быть больше 0'}
            )
        return data

    def save_ingredients(self, recipe, ingredients_data):
        ingredients_objs = [
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ing['id'],
                amount=ing['amount']
            )
            for ing in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(ingredients_objs)

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        image_base64 = validated_data.pop('image')
        format, imgstr = image_base64.split(';base64,')
        ext = format.split('/')[-1]
        image_data = base64.b64decode(imgstr)
        unique_filename = f'{uuid.uuid4()}.{ext}'
        image_file = ContentFile(image_data, name=unique_filename)
        recipe = Recipe.objects.create(image=image_file, **validated_data)
        recipe.tags.set(tags)
        self.save_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        ingredients_data = validated_data.pop('ingredients', None)
        image_base64 = validated_data.pop('image', None)
        if image_base64:
            format, imgstr = image_base64.split(';base64,')
            ext = format.split('/')[-1]
            image_data = base64.b64decode(imgstr)
            unique_filename = f'{uuid.uuid4()}.{ext}'
            image_file = ContentFile(image_data, name=unique_filename)
            instance.image = image_file
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            self.save_ingredients(instance, ingredients_data)
        return instance


class UserWithRecipesSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count')

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = obj.recipes.all()[:6]
        serializer = RecipeSerializer(
            recipes, many=True, context={
                'request': request})
        return serializer.data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class SubscriptionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='author.id', read_only=True)
    email = serializers.EmailField(source='author.email', read_only=True)
    username = serializers.CharField(source='author.username', read_only=True)
    first_name = serializers.CharField(
        source='author.first_name', read_only=True)
    last_name = serializers.CharField(
        source='author.last_name', read_only=True)
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
        )

    def get_is_subscribed(self, obj):
        return True

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = obj.author.recipes.all()
        limit = request.query_params.get('recipes_limit')
        if limit:
            recipes = recipes[: int(limit)]
        return RecipeSerializer(
            recipes, many=True, context={
                'request': request}).data

    def get_recipes_count(self, obj):
        return obj.author.recipes.count()


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Subscription
        fields = ('author',)

    def validate(self, data):
        user = self.context['request'].user
        author = data['author']
        if user == author:
            raise serializers.ValidationError('Нельзя подписаться на себя')
        if user.follower.filter(author=author).exists():
            raise serializers.ValidationError('Уже подписан')
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        author = validated_data['author']
        return Subscription.objects.create(user=user, author=author)


class FavoriteSerializer(serializers.ModelSerializer):
    recipe = RecipeMinfieldSerializer(read_only=True)
    recipe_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Favorite
        fields = ('id', 'user', 'recipe', 'recipe_id')
        read_only_fields = ('user',)

    def validate_recipe_id(self, value):
        get_object_or_404(Recipe, id=value)
        return value

    def validate(self, data):
        user = self.context['request'].user
        recipe_id = data.get('recipe_id')
        if (recipe_id and Favorite.objects.filter(
                user=user, recipe_id=recipe_id).exists()):
            raise serializers.ValidationError('Рецепт уже в избранном')
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        recipe = get_object_or_404(Recipe, id=validated_data['recipe_id'])
        return Favorite.objects.create(user=user, recipe=recipe)


class ShoppingCartSerializer(serializers.ModelSerializer):
    recipe = RecipeMinfieldSerializer(read_only=True)
    recipe_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ShoppingCart
        fields = ('id', 'user', 'recipe', 'recipe_id')
        read_only_fields = ('user',)

    def validate_recipe_id(self, value):
        get_object_or_404(Recipe, id=value)
        return value

    def validate(self, data):
        user = self.context['request'].user
        recipe_id = data.get('recipe_id')
        if (recipe_id and ShoppingCart.objects.filter(
                user=user, recipe_id=recipe_id).exists()):
            raise serializers.ValidationError('Рецепт уже в корзине')
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        recipe = get_object_or_404(Recipe, id=validated_data['recipe_id'])
        return ShoppingCart.objects.create(user=user, recipe=recipe)


class AvatarSerializer(serializers.ModelSerializer):
    avatar = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)

    def validate_avatar(self, value):
        if not value:
            raise serializers.ValidationError('Изображение обязательно')
        if not value.startswith('data:image'):
            raise serializers.ValidationError('Неверный формат изображения')
        return value

    def update(self, instance, validated_data):
        avatar_base64 = validated_data.get('avatar')
        if avatar_base64:
            format, imgstr = avatar_base64.split(';base64,')
            ext = format.split('/')[-1]
            image_data = base64.b64decode(imgstr)
            unique_filename = f'avatar_{uuid.uuid4()}.{ext}'
            image_file = ContentFile(image_data, name=unique_filename)
            instance.avatar = image_file
            instance.save()
        return instance
