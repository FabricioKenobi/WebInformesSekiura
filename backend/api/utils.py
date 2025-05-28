from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

def enviar_mail_desde_usuario(usuario, asunto, cuerpo_html, destinatarios, cc=None):
    texto_plano = strip_tags(cuerpo_html)

    email = EmailMultiAlternatives(
        subject=asunto,
        body=texto_plano,
        from_email=usuario.smtp_credenciales.email,
        to=destinatarios,
        cc=cc or [],
    )
    email.attach_alternative(cuerpo_html, "text/html")
    email.send()