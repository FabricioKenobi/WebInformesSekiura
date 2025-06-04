from django.contrib.auth.models import User
from rest_framework import serializers
from .models import CredencialesSMTP

class CredencialesSMTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = CredencialesSMTP
        fields = ['smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'email_remitente']

    
class UserSerializer(serializers.ModelSerializer):
    credenciales_smtp = CredencialesSMTPSerializer(required=False)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "credenciales_smtp"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        smtp_data = validated_data.pop("credenciales_smtp", None)
        user = User.objects.create_user(**validated_data)
        if smtp_data:
            CredencialesSMTP.objects.create(user=user, **smtp_data)
        return user

    def update(self, instance, validated_data):
        smtp_data = validated_data.pop("credenciales_smtp", None)
        instance.email = validated_data.get("email", instance.email)
        instance.username = validated_data.get("username", instance.username)
        if "password" in validated_data:
            instance.set_password(validated_data["password"])
        instance.save()

        if smtp_data:
            CredencialesSMTP.objects.update_or_create(user=instance, defaults=smtp_data)

        return instance
    
