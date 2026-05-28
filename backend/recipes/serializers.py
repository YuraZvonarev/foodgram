import base64

from django.core.files.base import ContentFile
from rest_framework import serializers
from users.serializers import UserSerializer

from .models import Ingredient, Recipe, RecipeIngredient, Tag


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
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients', many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'name', 'image', 'text',
                  'cooking_time'
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


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True)
    ingredients = serializers.ListField(
        child=serializers.DictField(), write_only=True)
    image = serializers.CharField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'ingredients', 'name',
                  'image', 'text', 'cooking_time')

    def validate(self, data):
        if data['cooking_time'] <= 0:
            raise serializers.ValidationError(
                {'cooking_time': 'Время приготовления должно быть больше 0'})
        if not data.get('ingredients'):
            raise serializers.ValidationError(
                {'ingredients': 'Нужны ингредиенты'})
        for ingredient in data['ingredients']:
            if 'id' not in ingredient or 'amount' not in ingredient:
                raise serializers.ValidationError(
                    {'ingredients': 'Укажите id и amount'})
            if ingredient['amount'] <= 0:
                raise serializers.ValidationError(
                    {'ingredients': 'Количество должно быть больше 0'})
        return data

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        image_base64 = validated_data.pop('image')
        format, imgstr = image_base64.split(';base64,')
        ext = format.split('/')[-1]
        image_data = base64.b64decode(imgstr)
        image_file = ContentFile(image_data, name=f'temp.{ext}')
        recipe = Recipe.objects.create(image=image_file, **validated_data)
        recipe.tags.set(tags)
        for ing in ingredients_data:
            ingredient = Ingredient.objects.get(id=ing['id'])
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                amount=ing['amount']
            )
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        ingredients_data = validated_data.pop('ingredients', None)
        image_base64 = validated_data.pop('image', None)
        if image_base64:
            format, imgstr = image_base64.split(';base64,')
            ext = format.split('/')[-1]
            image_data = base64.b64decode(imgstr)
            image_file = ContentFile(image_data, name=f'temp.{ext}')
            instance.image = image_file
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            for ing in ingredients_data:
                ingredient = Ingredient.objects.get(id=ing['id'])
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=ingredient,
                    amount=ing['amount']
                )
        return instance
