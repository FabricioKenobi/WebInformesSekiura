from django.shortcuts import render
from django.contrib.auth.models import User
from rest_framework import generics
from .serializers import UserSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Nota
from django.shortcuts import render, redirect 
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login




class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]



def login_view(request):
    if request.method == 'POST':
        user = authenticate(username=request.POST['username'], password=request.POST['password'])
        if user:
            login(request, user)
            return redirect('home')  # <- asegurate que esta url exista
        else:
            return render(request, 'login.html', {'error': 'Credenciales incorrectas'})
    return render(request, 'login.html')

def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1 != password2:
            return render(request, 'register.html', {'error': 'Las contraseñas no coinciden'})

        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Ese nombre de usuario ya existe'})

        user = User.objects.create_user(username=username, email=email, password=password1)
        user.save()
        return redirect('login')  # O a una página de bienvenida

    return render(request, 'register.html')

@login_required
def home_view(request):
    notas = Nota.objects.filter(usuario=request.user).order_by('-fecha_creacion')
    return render(request, 'home.html', {'notas': notas})

@login_required
def crear_nota_view(request):
    if request.method == 'POST':
        titulo = request.POST['titulo']
        contenido = request.POST['contenido']
        tipo = request.POST['tipo']

        if not titulo or not contenido or not tipo:
            return render(request, 'crear_nota.html', {'error': 'Todos los campos son obligatorios'})

        Nota.objects.create(
            titulo=titulo,
            contenido=contenido,
            tipo=tipo,
            usuario=request.user
        )
        return redirect('home')

    return render(request, 'crear_nota.html')