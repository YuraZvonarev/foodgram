from rest_framework.routers import DefaultRouter
from .views import TagViewSet, IngredientViewSet, RecipeViewSet, UserViewSet

router_v1 = DefaultRouter()
router_v1.register(r'tags', TagViewSet, basename='tag')
router_v1.register(r'ingredients', IngredientViewSet, basename='ingredient')
router_v1.register(r'recipes', RecipeViewSet, basename='recipe')
router_v1.register(r'users', UserViewSet, basename='user')

urlpatterns = router_v1.urls
