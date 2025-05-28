from django.contrib import admin
from django.urls import path, include
from api.views import CreateUserView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from api.views import login_view, register_view,home_view, crear_nota_view,crear_email_view, crear_email_personalizado, crear_cliente_view, crear_plantilla_view, probar_envio_email
from django.contrib.auth.views import LogoutView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/user/register/", CreateUserView.as_view(), name="register"),
    path("api/token/", TokenObtainPairView.as_view(), name="get_token"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("api-auth/", include("rest_framework.urls")),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('', home_view, name='home'),  # Landing page después del login
    path('crear-nota/', crear_nota_view, name='crear_nota'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('crear-email/', crear_email_view, name='crear_email'),
    path('crear_email_personalizado/', crear_email_personalizado, name='crear_email_personalizado'),
    path('crear_cliente/', crear_cliente_view, name='crear_cliente'),
    path('crear_plantilla/', crear_plantilla_view, name='crear_plantilla'),
    path('probar-mail/', probar_envio_email, name='probar_mail'),
]