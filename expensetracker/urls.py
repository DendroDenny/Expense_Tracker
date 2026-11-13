from django.urls import include, path

from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('home/', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('api/', include('expensetracker.api_urls')),
]