from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives, send_mail, get_connection
from django.utils.html import strip_tags
from django.template.defaultfilters import date as date_filter
from django.http import HttpResponse
from .models import Nota, mail, Cliente, EmailEnviado, PlantillaEmail
from .serializers import UserSerializer
from email.mime.image import MIMEImage
from .forms import CredencialesSMTPForm
from .models import CredencialesSMTP

class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

@login_required
def configurar_correo(request):
    try:
        credenciales = request.user.credenciales_smtp
    except CredencialesSMTP.DoesNotExist:
        credenciales = None

    if request.method == 'POST':
        form = CredencialesSMTPForm(request.POST, request.FILES, instance=credenciales)
        if form.is_valid():
            smtp = form.save(commit=False)
            smtp.user = request.user
            smtp.save()
            return redirect('home')  # o a donde quieras
    else:
        form = CredencialesSMTPForm(instance=credenciales)

    return render(request, 'configurar_correo.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        user = authenticate(username=request.POST['username'], password=request.POST['password'])
        if user:
            login(request, user)
            return redirect('home')
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
        return redirect('configurar_correo')

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
        return redirect('home')

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
        user = request.user
        creds = user.credenciales_smtp
        cliente = Cliente.objects.get(id=request.POST['cliente'])
        asunto = request.POST['asunto']
        cuerpo_html = request.POST['cuerpo']
        fecha_1 = request.POST.get('fecha_1')
        fecha_2 = request.POST.get('fecha_2')
        archivo = request.FILES.get("archivo_adjunto")
        firma = request.user.credenciales_smtp.imagen

        from datetime import datetime
        fecha_1 = datetime.strptime(fecha_1, "%Y-%m-%d")
        fecha_2 = datetime.strptime(fecha_2, "%Y-%m-%d")

        fecha_1_str = date_filter(fecha_1, "l d/M")
        fecha_2_str = date_filter(fecha_2, "l d/M")

        asunto_final = asunto.replace('{cliente}', cliente.nombre)
        cuerpo_html_final = cuerpo_html.replace('{cliente}', cliente.nombre)
        cuerpo_html_final = cuerpo_html_final.replace('{fecha_1}', fecha_1_str)
        cuerpo_html_final = cuerpo_html_final.replace('{fecha_2}', fecha_2_str)
        cuerpo_html_final = cuerpo_html_final.replace('{imagen}', '<img src="cid:imagen_incrustada">')

        cuerpo_texto = strip_tags(cuerpo_html_final)
        destino = cliente.email_1
        
        connection = get_connection(
            host=creds.smtp_host,
            port=creds.smtp_puerto,
            username=creds.smtp_user,
            password=creds.smtp_password,
            #use_tls=False
            use_ssl=True
        )

        email = EmailMultiAlternatives(
            subject=asunto_final,
            body=cuerpo_texto,
            from_email=creds.email_remitente,
            to=[destino],
            connection= connection
        )
        email.attach_alternative(cuerpo_html_final, "text/html")
        if firma:
            image = MIMEImage(firma.read())
            image.add_header('Content-ID', '<imagen_incrustada>')  # El ID entre < >
            image.add_header('Content-Disposition', 'inline', filename=firma.name)
            email.attach(image)

        # 3. Modificar el HTML para incluir la imagen
        
        if archivo:
            email.attach(archivo.name, archivo.read(), archivo.content_type)
        email.send()

        EmailEnviado.objects.create(
            usuario=request.user,
            cliente=cliente,
            asunto=asunto_final,
            cuerpo=cuerpo_html_final,
            enviado=True,
            fecha_evento=fecha_1,
            fecha_envio=timezone.now(),
            archivo_adjunto=archivo
        )

        return redirect('home')

    clientes = Cliente.objects.all()
    plantillas = PlantillaEmail.objects.all()
    return render(request, 'crear_email_personalizado.html', {
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

def probar_envio_email(request):
    try:
        user = request.user
        creds = user.credenciales_smtp
        connection = get_connection(
            host='mail.sekiura.com.py',
            port=465,
            username=creds.smtp_user,
            password=creds.smtp_password,
            #use_tls=False
            use_ssl=True

        )
        send_mail(
            subject='Correo de prueba',
            message='Este es un mensaje de prueba enviado desde Django.',
            from_email=creds.email_remitente,
            recipient_list=['fabriciojoel99@gmail.com'],
            fail_silently=False,
            connection=connection
        )
        return HttpResponse("Correo enviado exitosamente.")
    except Exception as e:
        return HttpResponse(f"Error al enviar correo: {str(e)}")

def soc_home(request):
    plantillas = PlantillaEmail.objects.all()
    clientes = Cliente.objects.all()
    return render(request, 'soc_home.html', {
        'plantillas': plantillas,
        'clientes': clientes,
    })
