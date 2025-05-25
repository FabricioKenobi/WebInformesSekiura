from django.contrib import admin
from django.urls import path, include
from api.views import CreateUserView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from api.views import login_view, register_view,home_view, crear_nota_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/user/register/", CreateUserView.as_view(), name="register"),
    path("api/token/", TokenObtainPairView.as_view(), name="get_token"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("api-auth/", include("rest_framework.urls")),
    path("api/", include("api.urls")),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('', home_view, name='home'),  # Landing page después del login
    path('crear-nota/', crear_nota_view, name='crear_nota'),
]