from django.shortcuts import render
from django.contrib.auth.models import User
from rest_framework import generics
from .serializers import UserSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Nota, mail, Cliente, EmailEnviado, PlantillaEmail
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

@login_required
def crear_email_view(request):
    if request.method == 'POST':
        asunto = request.POST['asunto']
        fecha_evento = request.POST['fecha_evento']
        cuerpo = request.POST['cuerpo']

        if not asunto or not fecha_evento or not cuerpo:
            return render(request, 'crear_email.html', {'error': 'Todos los campos son obligatorios'})

        mail.objects.create(
            asunto=asunto,
            fecha_evento=fecha_evento,
            cuerpo=cuerpo,
            usuario=request.user
        )
        return redirect('home')  # o una página de confirmación

    return render(request, 'crear_mail.html')


@login_required
def crear_cliente_view(request):
    if request.method == 'POST':
        nombre = request.POST['nombre']
        campos = ['email_1', 'email_2', 'email_3', 'email_4', 'email_5', 'email_6', 'cc_1', 'cc_2']
        datos = {campo: request.POST.get(campo) for campo in campos}

        cliente = Cliente(nombre=nombre, **datos)
        cliente.save()
        return redirect('home')

    return render(request, 'crear_cliente.html')

@login_required
def crear_email_personalizado(request):
    clientes = Cliente.objects.all()
    plantillas = PlantillaEmail.objects.all()

    if request.method == 'POST':
        cliente_id = request.POST['cliente']
        plantilla_id = request.POST['plantilla']
        fecha_evento = request.POST['fecha_evento']
        cuerpo_editado = request.POST['cuerpo']

        cliente = Cliente.objects.get(id=cliente_id)
        plantilla = PlantillaEmail.objects.get(id=plantilla_id)

        # Reemplazar fecha en cuerpo
        cuerpo = plantilla.cuerpo_base.replace("{fecha}", fecha_evento)
        asunto = plantilla.asunto

        # Recolectar todos los emails válidos
        to_emails = [getattr(cliente, f"email_{i}") for i in range(1, 7) if getattr(cliente, f"email_{i}")]
        cc_emails = [cliente.cc_1, cliente.cc_2]
        cc_emails = [c for c in cc_emails if c]

        # Crear y guardar el email (registro)
        email_enviado = EmailEnviado.objects.create(
            cliente=cliente,
            plantilla=plantilla,
            fecha_evento=fecha_evento,
            asunto=asunto,
            cuerpo=cuerpo_editado or cuerpo,
            enviado=False,
        )


        email_enviado.enviado = True
        email_enviado.save()

        return redirect('home')

    return render(request, 'crear_email_personalizado.html', {
        'clientes': clientes,
        'plantillas': plantillas,
    })