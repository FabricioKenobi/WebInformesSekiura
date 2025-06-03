from django import forms
from .models import CredencialesSMTP

class CredencialesSMTPForm(forms.ModelForm):
    class Meta:
        model = CredencialesSMTP
        fields = ['smtp_user', 'smtp_password', 'smtp_host', 'smtp_puerto', 'email_remitente','imagen']
        widgets = {
            'smtp_password': forms.PasswordInput(),
        }
