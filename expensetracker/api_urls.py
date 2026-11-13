from rest_framework.routers import DefaultRouter

from .api_views import ExpenseViewSet

router = DefaultRouter()
router.register('expenses', ExpenseViewSet, basename='expense')

urlpatterns = router.urls
