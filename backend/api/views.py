from django.shortcuts import render
from django.contrib.auth.models import User
from rest_framework import generics
from .serializers import UserSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Nota, mail, Cliente, EmailEnviado, PlantillaEmail
from django.shortcuts import render, redirect 
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend


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
    emails = EmailEnviado.objects.filter(usuario=request.user).order_by('-fecha_envio')[:20]
    return render(request, 'home.html', {'emails': emails})

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
    if request.method == 'POST':
        cliente = Cliente.objects.get(id=request.POST['cliente'])
        asunto = request.POST['asunto']
        cuerpo_html = request.POST['cuerpo']
        cuerpo_texto = strip_tags(cuerpo_html)  # versión texto plano
        destino = cliente.email_1  # o una lista dinámica

        # Usar SMTP personalizado del usuario logueado
        backend = EmailBackend(
            host='mail.tudominio.com',
            port=587,
            username=request.user.smtp_email,
            password=request.user.smtp_password,
            use_tls=True,
            fail_silently=False,
        )

        email = EmailMultiAlternatives(
            subject=asunto,
            body=cuerpo_texto,
            from_email=request.user.smtp_email,
            to=[destino],
            connection=backend
        )
        email.attach_alternative(cuerpo_html, "text/html")
        email.send()

        # Guardar email en la base si querés
        EmailEnviado.objects.create(
            usuario=request.user,
            cliente=cliente,
            asunto=asunto,
            cuerpo=cuerpo_html,
            enviado=True,
            fecha_evento=request.POST['fecha_1'],
            fecha_envio=timezone.now()
        )

        return redirect('home')

    # GET
    clientes = Cliente.objects.all()
    plantillas = PlantillaEmail.objects.all()
    return render(request, 'notas/crear_email_personalizado.html', {
        'clientes': clientes,
        'plantillas': plantillas,
    })
    


@login_required
def crear_plantilla_view(request):
    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        asunto = request.POST.get('asunto')
        cuerpo = request.POST.get('cuerpo_base', '')

        if not cuerpo:
            return render(request, 'crear_plantilla.html', {
                'error': 'El cuerpo no fue recibido.'
            })

        PlantillaEmail.objects.create(
            tipo=tipo,
            asunto=asunto,
            cuerpo_base=cuerpo
        )
        return redirect('home')

    return render(request, 'crear_plantilla.html')

