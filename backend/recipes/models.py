from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

User = settings.AUTH_USER_MODEL


class Tag(models.Model):
    name = models.CharField(max_length=200, unique=True,
                            verbose_name='Название')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='Слаг')

    class Meta:
        ordering = ('name',)
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название')
    measurement_unit = models.CharField(
        max_length=50, verbose_name='Единица измерения')

    class Meta:
        ordering = ('name',)
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        constraints = [
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'), name='unique_ingredient')
        ]

    def __str__(self):
        return f'{self.name} ({self.measurement_unit})'


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор')
    name = models.CharField(max_length=200, verbose_name='Название')
    image = models.ImageField(
        upload_to='recipes/image/', verbose_name='Картинка')
    text = models.TextField(verbose_name='Описание')
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингредиенты')
    tags = models.ManyToManyField(
        Tag, related_name='recipes', verbose_name='Теги')
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления', validators=[MinValueValidator(1)])
    pub_date = models.DateTimeField(
        auto_now_add=True, verbose_name='Дата публикации')

    class Meta:
        ordering = ('-pub_date',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='recipe_ingredients', verbose_name='Рецепт')
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Ингредиент')
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество', validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        constraints = [
            models.UniqueConstraint(
                fields=(
                    'recipe',
                    'ingredient'),
                name='unique_ingredient_in_recipe')]

    def __str__(self):
        return (
            f'{self.ingredient.name} - '
            f'{self.amount} {self.ingredient.measurement_unit}'
        )


class Favorite(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='favorites', verbose_name='Пользователь')
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='favorited_by', verbose_name='Рецепт')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'), name='unique_favorite')
        ]
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные'

    def __str__(self):
        return f'{self.user} добавил {self.recipe} в избранное'


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='shopping_cart')
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='in_shopping_cart')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'), name='unique_shopping_cart')
        ]
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

    def __str__(self):
        return f'{self.user} добавил {self.recipe} в корзину'
