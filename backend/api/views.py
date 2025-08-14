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
    for m in emails:
        if isinstance(m.asunto, str):
            i = m.asunto.find("Informe")
            if i != -1:
                m.asunto = m.asunto[i:]

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
def guardar_email_personalizado(request):
    from datetime import datetime
    from django.utils import timezone
    import os
    import glob
    from django.core.files import File
    
    if request.method == 'POST':
        user = request.user
        cliente = Cliente.objects.get(id=request.POST['cliente'])
        asunto = request.POST['asunto']
        cuerpo_html = request.POST.get("cuerpo_html", "")
        url_informe = request.POST.get("url_informe","")
        nombreArch = request.POST.get("nombreArch","")
        
        # Procesamiento de fechas
        fecha_1_str = request.POST.get('fecha_1', '')
        fecha_2_str = request.POST.get('fecha_2', '')
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

        # Reemplazar placeholders
        asunto_final = asunto.replace('{cliente}', cliente.nombre)
        cuerpo_html_final = cuerpo_html.replace('{cliente}', cliente.nombre)
        cuerpo_html_final = cuerpo_html_final.replace('{fecha_1}', fecha_1_str)
        cuerpo_html_final = cuerpo_html_final.replace('{fecha_2}', fecha_2_str)
        cuerpo_html_final = cuerpo_html_final.replace('{imagen}', '<img src="cid:firma_incrustada" style="max-width:100%">')
        
        # Formatear texto para HTML
        cuerpo_html_final = cuerpo_html_final.replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')
        cuerpo_html_final = cuerpo_html_final.replace('  ', '&nbsp;&nbsp;')
        cuerpo_html_final = cuerpo_html_final.replace('\n', '<br>')

        # Manejo del archivo adjunto
        archivo_adjunto = None
        
        # 1. Primero verificar si hay un archivo subido en el request
        if 'archivo_adjunto' in request.FILES:
            archivo_adjunto = request.FILES['archivo_adjunto']
        else:
            # 2. Si no hay archivo subido, buscar el PDF generado
            carpeta = "/home/hermes/WebInformesSekiura/backend/"
            patron = f"{cliente.nombre}-Informe-Ejecutivo-*"
            archivos = glob.glob(os.path.join(carpeta, patron))
            
            if archivos:
                ultimo_archivo = max(archivos, key=os.path.getmtime)
                # Leer el contenido del archivo y crear un ContentFile
                with open(ultimo_archivo, 'rb') as f:
                    file_content = f.read()
                from django.core.files.base import ContentFile
                archivo_adjunto = ContentFile(file_content, name=os.path.basename(ultimo_archivo))

        # Crear el borrador
        borrador = EmailEnviado(
            usuario=request.user,
            cliente=cliente,
            asunto=asunto_final,
            cuerpo=cuerpo_html_final,
            enviado=False,
            fecha_evento=timezone.now(),
            url_informe=url_informe,
            
            nombreArch =nombreArch
        )

        # Asignar el archivo adjunto si existe
        if archivo_adjunto:
            borrador.archivo_adjunto.save(
                archivo_adjunto.name,
                archivo_adjunto,
                save=True
            )
        else:
            borrador.save()

        return redirect('home')  
    
    clientes = Cliente.objects.all()
    plantillas = PlantillaEmail.objects.all()
    return render(request, 'soc_home.html', {
        'clientes': clientes,
        'plantillas': plantillas,
    })

@login_required
def enviar_email_guardado(request, email_id):
    from django.utils import timezone
    import os
    import glob
    from django.core.mail import EmailMultiAlternatives, get_connection
    from email.mime.image import MIMEImage
    
    # Obtener el email guardado
    try:
        email_guardado = EmailEnviado.objects.get(id=email_id, usuario=request.user, enviado=False)
    except EmailEnviado.DoesNotExist:
        return HttpResponse("Email no encontrado o ya fue enviado", status=404)
    
    # Obtener credenciales SMTP del usuario
    creds = request.user.credenciales_smtp
    
    # Obtener lista de emails del cliente
    cliente = email_guardado.cliente
    emails = filter(None, [
        cliente.email_1, cliente.email_2, cliente.email_3,
        cliente.email_4, cliente.email_5, cliente.email_6,
        cliente.cc_1, cliente.cc_2
    ])
    to = list(emails)
    
    # Configurar conexión SMTP
    connection = get_connection(
        host=creds.smtp_host,
        port=creds.smtp_puerto,
        username=creds.smtp_user,
        password=creds.smtp_password,
        use_ssl=True
    )
    
    # Crear el email
    email = EmailMultiAlternatives(
        subject=email_guardado.asunto,
        from_email=creds.email_remitente,
        to=to,
        connection=connection
    )
    email.mixed_subtype = 'related'
    
    # Adjuntar imagen de firma
    firma_path = os.path.join(settings.BASE_DIR, 'api', 'static', 'img', 'firma.png')
    with open(firma_path, 'rb') as f:
        img = MIMEImage(f.read(), _subtype='png')
        img.add_header('Content-ID', '<firma_incrustada>')
        img.add_header('Content-Disposition', 'inline', filename='firma.png')
        email.attach(img)
    
    email.attach_alternative(email_guardado.cuerpo, "text/html")
    
    # Adjuntar archivo PDF si existe
    if email_guardado.archivo_adjunto:
        with open(email_guardado.archivo_adjunto.path, 'rb') as f:
            email.attach(
                os.path.basename(email_guardado.archivo_adjunto.name),
                f.read(),
                'application/pdf'
            )
    
    # Intentar enviar el email
    try:
        email.send()
        # Marcar como enviado y actualizar fecha
        email_guardado.enviado = True
        email_guardado.fecha_envio = timezone.now()
        email_guardado.save()
        
        # Eliminar archivo adjunto si es necesario
        if email_guardado.archivo_adjunto:
            try:
                os.remove(email_guardado.archivo_adjunto.path)
            except Exception as e:
                print(f"No se pudo eliminar el archivo adjunto: {e}")
        
        return redirect('home')
    
    except Exception as e:
        print("Error al enviar correo:", e)
        return HttpResponse(f"Error al enviar el correo: {str(e)}", status=500)
    
def lista_borradores(request):
    # Filtra solo los borradores
    borradores = EmailEnviado.objects.filter(enviado=False).order_by('-fecha_evento')
    
    context = {
        'emails': borradores
    }
    for m in borradores:
        if isinstance(m.asunto, str):
            i = m.asunto.find("Informe")
            if i != -1:
                m.asunto = m.asunto[i:]
                
    return render(request, 'lista_borradores.html', context)

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
def editar_borrador(request, email_id):
    try:
        borrador = EmailEnviado.objects.get(id=email_id, usuario=request.user, enviado=False)
    except EmailEnviado.DoesNotExist:
        raise Http404("Borrador no encontrado")

    if request.method == 'POST':
        # Procesar el formulario de edición
        borrador.asunto = request.POST.get('asunto')
        borrador.cuerpo = request.POST.get('cuerpo_html')
        if 'archivo_adjunto' in request.FILES:
            borrador.archivo_adjunto = request.FILES['archivo_adjunto']
        borrador.save()
        return redirect('home')

    clientes = Cliente.objects.all()
    plantillas = PlantillaEmail.objects.all()
    
    return render(request, 'editar_borrador.html', {
        'borrador': borrador,
        'clientes': clientes,
        'plantillas': plantillas,
    })
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django.core.files import File
from django.utils.text import slugify
# utils de filename (colocá esto en el mismo archivo o en un utils.py)
import re, unicodedata

def sanitize_filename_preserve_case(value: str) -> str:
    # Normaliza a ASCII sin alterar mayúsculas/minúsculas
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    # Espacios a guiones
    value = re.sub(r"\s+", "-", value)
    # Quitar caracteres inválidos típicos en nombres de archivo
    value = re.sub(r'[\\/*?:"<>|]', "-", value)
    # Permitir solo [A-Za-z0-9._-]
    value = re.sub(r"[^A-Za-z0-9._-]", "", value)
    # Colapsar guiones repetidos y recortar bordes
    value = re.sub(r"-{2,}", "-", value).strip("-_.")
    return value or "Informe"
@csrf_exempt
@login_required
def guardar_borrador(request, borrador_id):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'})

    try:
        borrador = EmailEnviado.objects.get(pk=borrador_id)

        base_por_defecto = borrador.nombreArch or os.path.basename(borrador.archivo_adjunto.name or '') or 'informe'

        nombre_arch_base = (request.POST.get('nombreArch') or os.path.splitext(base_por_defecto)[0]).strip() or 'informe'
        base_clean = sanitize_filename_preserve_case(os.path.splitext(nombre_arch_base)[0] or "Informe")
        nombre_final_pdf = base_clean + ".pdf"

        def overwrite_filefield_with(final_name_basename, fileobj):
            if borrador.archivo_adjunto:
                try:
                    borrador.archivo_adjunto.delete(save=False)
                except Exception:
                    pass
            borrador.archivo_adjunto.save(final_name_basename, fileobj, save=False)
            borrador.nombreArch = final_name_basename

        uploaded_file = request.FILES.get('archivo_adjunto')
        nombre_archivo_generado = (request.POST.get('nombre_archivo_guardado') or '').strip()

        # === FAIL-FAST: si no hay ninguna fuente, avisar y NO devolver ok ===
        if not uploaded_file and not nombre_archivo_generado:
            return JsonResponse({
                'ok': False,
                'error': 'No se recibió archivo a subir ni nombre de archivo generado (nombre_archivo_guardado).'
            })

        if uploaded_file:
            overwrite_filefield_with(nombre_final_pdf, uploaded_file)

        else:
            # Usar el PDF generado por tu backend
            tmp_input = nombre_archivo_generado
            tmp_basename = os.path.basename(tmp_input)

            if not tmp_basename.lower().endswith(".pdf"):
                tmp_basename_pdf = tmp_basename + ".pdf"
            else:
                tmp_basename_pdf = tmp_basename

            candidate_paths = []

            if os.path.isabs(tmp_input):
                candidate_paths.append(tmp_input)
                if not tmp_input.lower().endswith(".pdf"):
                    candidate_paths.append(tmp_input + ".pdf")

            candidate_paths.append(os.path.join(settings.MEDIA_ROOT, "archivos", tmp_basename_pdf))
            candidate_paths.append(os.path.join(settings.MEDIA_ROOT, tmp_basename_pdf))
            candidate_paths.append(os.path.join("/home/hermes/WebInformesSekiura/backend", tmp_basename_pdf))

            src_path = next((p for p in candidate_paths if os.path.exists(p)), None)
            if not src_path:
                return JsonResponse({
                    'ok': False,
                    'error': f'No existe el archivo generado: {tmp_basename}. Probé: ' + " | ".join(candidate_paths)
                })

            with open(src_path, 'rb') as fh:
                overwrite_filefield_with(nombre_final_pdf, File(fh))

            try:
                arch_dir = os.path.join(settings.MEDIA_ROOT, "archivos")
                if src_path.startswith(arch_dir) and os.path.basename(src_path) != nombre_final_pdf:
                    os.remove(src_path)
            except Exception:
                pass

        # Guardar el resto de campos
        borrador.asunto = request.POST.get('asunto', borrador.asunto)
        borrador.cuerpo = request.POST.get('cuerpo_html', borrador.cuerpo)
        
        borrador.url_informe = request.POST.get('url_informe', borrador.url_informe)

        borrador.save()
        return JsonResponse({'ok': True})

    except EmailEnviado.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Borrador no encontrado'})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})

    

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
import time  # <-- Añade esta importación

informe = ""

@csrf_exempt
@login_required
def ejecutar_comando_cliente(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            informe_url = data.get('informe')
            nombre_archivo = data.get('nombreArch', 'informe').replace(' ', '_') + '.pdf'
            
            # Crear directorio específico con permisos adecuados
            informe_dir = os.path.join(settings.BASE_DIR, 'temp_pdfs')
            os.makedirs(informe_dir, exist_ok=True)
            os.chmod(informe_dir, 0o777)  # Asegurar permisos de escritura
            
            ruta_pdf = os.path.join(informe_dir, nombre_archivo)
            
            # Comando con parámetros adicionales para diagnóstico
            comando = [
                '/usr/local/bin/opensearch-reporting-cli',
                '--url', informe_url,
                '--auth', 'basic',
                '--credentials', 'sekiura-reports:Sekiura2025*',
                '--format', 'pdf',
                '--filename', ruta_pdf,
                '--timeout', '900',  # 15 minutos de timeout
                #'--debug'  # Modo debug para más información
            ]
            
            # Ejecutar comando con entorno completo
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                check=True,
                env={**os.environ, 'NODE_NO_WARNINGS': '1'}  # Suprimir advertencias de AWS SDK
            )
            
            # Verificación robusta del archivo generado
            if os.path.exists(ruta_pdf) and os.path.getsize(ruta_pdf) > 1024:  # Al menos 1KB
                return JsonResponse({
                    'ok': True,
                    'filename': nombre_archivo,
                    'path': ruta_pdf,
                    'download_url': f'/descargar-pdf/{nombre_archivo}',
                    'output': resultado.stdout
                })
            else:
                error_msg = "El PDF no se generó correctamente o está vacío"
                if os.path.exists(ruta_pdf):
                    error_msg += f" (Tamaño: {os.path.getsize(ruta_pdf)} bytes)"
                return JsonResponse({
                    'ok': False,
                    'error': error_msg,
                    'output': resultado.stdout,
                    'error_output': resultado.stderr,
                    
                })
                
        except subprocess.CalledProcessError as e:
            return JsonResponse({
                'ok': False,
                'error': f"Error en el comando (exit code {e.returncode}): {e.stderr}",
                'output': e.stdout,
                
            })
        except Exception as e:
            return JsonResponse({
                'ok': False,
                'error': str(e),
                
            })
        
from django.http import JsonResponse, FileResponse, Http404
import traceback
import urllib.parse

@csrf_exempt
@login_required
def ejecutar_comando_cliente(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    # 1) Parseamos JSON
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    informe = data.get('informe', '').strip()
    nombre = data.get('nombreArch', '').strip()
    
    if not informe:
        return JsonResponse({'ok': False, 'error': 'URL not specified'}, status=400)

    # 2) Normalizamos nombre a base + .pdf
    base, ext = os.path.splitext(nombre)
    nombre = f"{base}"
    

    # 3) Directorio y ruta completa
    output_dir  = "/home/hermes/WebInformesSekiura/backend"
    output_path = os.path.join(output_dir, nombre)
    nombre_rm = nombre.replace(' ', '\ ')
    output_path_rm = os.path.join(output_dir, nombre_rm)
    print(informe)
    from urllib.parse import unquote
    informe = unquote(informe)         # full decode
    informe2 = informe.replace("'",r"'\''")
    print(informe)
    print(output_path)
    # 5) Ejecutamos el CLI
    cmd = [
        "bash", "-c",
        # rm -f suprime el error si no existe; && sólo ejecuta el CLI si rm acaba sin error
        
        f"rm -f {output_path_rm}.pdf && "
        f"/usr/local/bin/opensearch-reporting-cli "
        f"--url '{informe2}' "
        f"--auth basic "
        f"--credentials 'sekiura-reports:Sekiura2025*' "
        f"--format pdf "
        f"--filename '{output_path}'"
    ]

    resultado = subprocess.run(cmd, cwd=output_dir, capture_output=True, text=True, check=False)

    if resultado.returncode != 0:
        return JsonResponse({
            'ok': False,
            'error': resultado.stderr.strip(),
            'returncode': resultado.returncode
        }, status=500)

    # 6) Devolvemos el nombre para la descarga
    return JsonResponse({
        'ok': True,
        'filename': nombre,
        'output': resultado.stdout.strip()
    })

from django.http import FileResponse, Http404

@login_required
def descargar_pdf(request, archivo_nombre):
    archivo_nombre += ".pdf"
    # 1) Validar que el nombre venga en la URL
    if not archivo_nombre:
        raise Http404("Nombre de archivo no especificado")

    # 2) Directorio correcto donde se generan los PDFs
    directorio = "/home/hermes/WebInformesSekiura/backend"

    # 3) Búsqueda case-insensitive
    nombre_buscado = archivo_nombre.lower()
    fichero_encontrado = None
    for fn in os.listdir(directorio):
        if fn.lower() == nombre_buscado:
            fichero_encontrado = fn
            break

    if not fichero_encontrado:
        raise Http404(f"El archivo «{archivo_nombre}» no existe en {directorio}")

    ruta_pdf = os.path.join(directorio, fichero_encontrado)

    # 4) Devolverlo como attachment
    return FileResponse(
        open(ruta_pdf, "rb"),
        content_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fichero_encontrado}"'}
    )