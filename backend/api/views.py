from django.shortcuts import render, redirect, get_object_or_404
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
from .models import  Cliente, EmailEnviado, PlantillaEmail
from .serializers import UserSerializer
from email.mime.image import MIMEImage
from .forms import CredencialesSMTPForm
from .models import CredencialesSMTP
import os
from django.conf import settings
from django.utils.dateparse import parse_date


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
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    emails = EmailEnviado.objects.all()

    if fecha_inicio:
        emails = emails.filter(fecha_envio__date__gte=parse_date(fecha_inicio))
    if fecha_fin:
        emails = emails.filter(fecha_envio__date__lte=parse_date(fecha_fin))

    emails = emails.order_by('-fecha_envio')
    
    return render(request, 'home.html', {
        'emails': emails,
    })


@login_required
def crear_cliente_view(request):
    if request.method == 'POST':
        nombre = request.POST['nombre']
        campos = ['email_1', 'email_2', 'email_3', 'email_4', 'email_5', 'email_6', 'cc_1', 'cc_2','IPSIEM','FQDN','diario','semanal','mensual']
        datos = {campo: request.POST.get(campo) for campo in campos}

        cliente = Cliente(nombre=nombre, **datos)
        cliente.save()
        return redirect('home')

    return render(request, 'crear_cliente.html')

@login_required
def crear_email_personalizado(request):
    from datetime import datetime  # Agrega esto al inicio con las demás importaciones
    from django.utils import timezone
    if request.method == 'POST':
        
        user = request.user
        creds = user.credenciales_smtp
        cliente = Cliente.objects.get(id=request.POST['cliente'])
        asunto = request.POST['asunto']
        cuerpo_html = request.POST.get("cuerpo_html")
        archivo = request.FILES.get("archivo_adjunto")
        
        # Asegurar valores de fechas
        fecha_1_str = request.POST.get('fecha_1', '')
        fecha_2_str = request.POST.get('fecha_2', '')

        contiene_imagen = '{imagen}' in cuerpo_html
        
        # Convertir fechas (manejar valores vacíos)
        fecha_1 = None
        fecha_2 = None
        date_format = "%Y-%m-%d"
        
        if fecha_1_str:
            fecha_1 = datetime.strptime(fecha_1_str, date_format)
            fecha_1_str = date_filter(fecha_1, "l d/M")
        else:
            fecha_1_str = ""

        if fecha_2_str:
            fecha_2 = datetime.strptime(fecha_2_str, date_format)
            fecha_2_str = date_filter(fecha_2, "l d/M")
        else:
            fecha_2_str = ""


        # Obtener cuerpo HTML directamente del request
        cuerpo_html = request.POST.get("cuerpo_html", "")
        
        # Reemplazar solo los placeholders necesarios
        asunto_final = asunto.replace('{cliente}', cliente.nombre)
        cuerpo_html_final = cuerpo_html.replace('{cliente}', cliente.nombre)
        cuerpo_html_final = cuerpo_html_final.replace('{fecha_1}', fecha_1_str)
        cuerpo_html_final = cuerpo_html_final.replace('{fecha_2}', fecha_2_str)
        #cuerpo_html_final = cuerpo_html_final.replace('{firma}', '<img src="../static/img/firma.png"  style="max-width:50%">')
        #cuerpo_html_final = cuerpo_html_final.replace('{imagen}', '<img src="cid:firma_incrustada"  style="max-width:100%">')
        
        
        

        cuerpo_texto = strip_tags(cuerpo_html_final)
        emails = filter(None, [cliente.email_1, cliente.email_2, cliente.email_3,cliente.email_4,cliente.email_5,cliente.email_6,cliente.cc_1,cliente.cc_2])
        to = list(emails)

        connection = get_connection(
            host=creds.smtp_host,
            port=creds.smtp_puerto,
            username=creds.smtp_user,
            password=creds.smtp_password,
            #use_tls=False
            use_ssl=True
        )
        cuerpo_html_final = cuerpo_html_final.replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')  # O más, como prefieras
        cuerpo_html_final = cuerpo_html_final.replace('  ', '&nbsp;&nbsp;')  # Opcional: dobles espacios por 2 &nbsp;
        cuerpo_html_final = cuerpo_html_final.replace('\n', '<br>')

        

        
        email = EmailMultiAlternatives(
            subject=asunto_final,
            #body=cuerpo_texto,
            from_email=creds.email_remitente,
            to=to,
            connection= connection
        )
        


        # Hacerlo multipart/related manualmente
        email.mixed_subtype = 'related'

        # Adjuntar imagen (firma)
        firma_path = os.path.join(settings.BASE_DIR, 'api', 'static', 'img', 'firma.png')
        with open(firma_path, 'rb') as f:
            img = MIMEImage(f.read(), _subtype='png')
            img.add_header('Content-ID', '<firma_incrustada>')
            img.add_header('Content-Disposition', 'inline', filename='firma.png')
            email.attach(img)
        email.attach_alternative(cuerpo_html_final, "text/html")
        

        # 3. Modificar el HTML para incluir la imagen
        print(informe)
        if archivo:
            email.attach(archivo.name, archivo.read(), archivo.content_type)
        output_path = os.path.join("/", informe+ ".pdf")
        if os.path.exists(output_path):
            with open(output_path, 'rb') as f:
                email.attach(informe + ".pdf", f.read(), 'application/pdf')
        try:
            email.send()
        except Exception as e:
            print("Error al enviar correo:", e)

        EmailEnviado.objects.create(
            usuario=request.user,
            cliente=cliente,
            asunto=asunto_final,
            cuerpo=cuerpo_html_final,
            enviado=True,
            fecha_evento=timezone.now(),
            fecha_envio=timezone.now(),
            archivo_adjunto=archivo
        )

        return redirect('home')
    
    clientes = Cliente.objects.all()
    plantillas = PlantillaEmail.objects.all()
    return render(request, 'soc_home.html', {
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


@login_required
def soc_home(request):
    if request.method == 'POST':
        user = request.user
        creds = user.credenciales_smtp

        cliente = Cliente.objects.get(id=request.POST['cliente'])
        asunto = request.POST['asunto']
        cuerpo_html = request.POST['cuerpo_html']
        
        archivo = request.FILES.get("archivo_adjunto")
        firma = request.user.credenciales_smtp.imagen

        from datetime import datetime
        from django.utils.timezone import now
        
        cuerpo_html_final = cuerpo_html.replace('{firma}', '<img src="cid:imagen_incrustada">')

        cuerpo_texto = strip_tags(cuerpo_html_final)
        destino = cliente.email_1

        connection = get_connection(
            host=creds.smtp_host,
            port=creds.smtp_puerto,
            username=creds.smtp_user,
            password=creds.smtp_password,
            use_ssl=True
        )

        email = EmailMultiAlternatives(
            subject=asunto,
            body=cuerpo_texto,
            from_email=creds.email_remitente,
            to=[destino],
            connection=connection
        )
        email.attach_alternative(cuerpo_html_final, "text/html")

        if firma:
            image = MIMEImage(firma.read())
            image.add_header('Content-ID', '<imagen_incrustada>')
            image.add_header('Content-Disposition', 'inline', filename=firma.name)
            email.attach(image)

        if archivo:
            email.attach(archivo.name, archivo.read(), archivo.content_type)

        email.send()

        # Guardar en base de datos
        EmailEnviado.objects.create(
            usuario=user,
            cliente=cliente,
            asunto=asunto,
            cuerpo=cuerpo_html_final,
            enviado=True,
            fecha_evento=now(),
            fecha_envio=now(),
            archivo_adjunto=archivo
        )

        return redirect('home')  # o donde quieras redirigir

    plantillas = PlantillaEmail.objects.all()
    clientes = Cliente.objects.all()
    return render(request, 'soc_home.html', {
        'plantillas': plantillas,
        'clientes': clientes,
    })

@login_required
def conf_cliente(request):
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')  # <-- El ID del cliente a actualizar
        
        campos = ['email_1', 'email_2', 'email_3', 'email_4', 'email_5', 'email_6', 'cc_1', 'cc_2','IPSIEM','FQDN','diario','semanal','mensual']
        datos = {campo: request.POST.get(campo) for campo in campos}

        cliente = get_object_or_404(Cliente, id=cliente_id)  # Si no existe, lanza 404
        for campo, valor in datos.items():
            setattr(cliente, campo, valor)  # Asigna dinámicamente cada campo
        cliente.save()

        return redirect('home')

    # Mostrar todos los clientes
    clientes = Cliente.objects.all()
    return render(request, 'clients.html', {
        'clientes': clientes,
    })
from django.views.decorators.csrf import csrf_exempt
import subprocess
import json
from django.http import JsonResponse

informe = ""

@csrf_exempt
@login_required
def ejecutar_comando_cliente(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            global informe
            informe = data.get('informe')
            nombreArch = data.get('nombreArch')
            
        
            # Ejecutar el comando en bash (ejemplo)
            resultado = subprocess.run(
            [
                #"cmd", "/c", "ping google.com"
                '/usr/local/bin/opensearch-reporting-cli',
                '--url', informe,
                '--auth', 'basic',
                '--credentials', 'sekiura-reports:Sekiura2025*',
                '--format', 'pdf',
                '--filename', nombreArch
            ],
                capture_output=True, text=True, check=True
            )
            

            return JsonResponse({'ok': True, 'output': resultado.stdout})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})
    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)