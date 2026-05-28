from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers

from .models import Subscription, User


class UserCreateSerializer(UserCreateSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username',
                  'first_name', 'last_name', 'password')


class UserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name',
                  'last_name', 'is_subscribed')

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return Subscription.objects.filter(user=user, author=obj).exists()
        return False


class SubscriptionSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='author.id')
    email = serializers.EmailField(source='author.email')
    username = serializers.CharField(source='author.username')
    first_name = serializers.CharField(source='author.first_name')
    last_name = serializers.CharField(source='author.last_name')
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ('id', 'email', 'username', 'first_name',
                  'last_name', 'us_subscribed', 'recipes', 'recipes_count')

        def get_is_subscribed(self, obj):
            return True

        def get_recipes(self, obj):
            request = self.context.get('request')
            recipes = obj.author.recipes.all()
            limit = request.query_params.get('recipes_limit')
            if limit:
                recipes = recipes[:int(limit)]
            from recipes.serializers import RecipeSerializer
            return RecipeSerializer(
                recipes, many=True, context={
                    'request': request}).data

        def get_recipes_count(self, obj):
            return obj.author.recipes.count()
