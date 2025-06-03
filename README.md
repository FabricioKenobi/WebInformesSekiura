# WebInformesSekiura

Aplicación web desarrollada con Django para la gestión y visualización de informes internos.

## 🚀 Requisitos

- Python 3.9 o superior  
- pip (gestor de paquetes de Python)  
- Git  

> Asegúrate de tener un entorno virtual activo para evitar conflictos de dependencias.

## 🛠️ Instalación

Sigue estos pasos para clonar el repositorio e iniciar el servidor localmente:

```bash
# 1. Clonar el repositorio
git clone https://github.com/FabricioKenobi/WebInformesSekiura

# 2. Entrar al directorio del proyecto
cd WebInformesSekiura

# 3. Instalar las dependencias del proyecto
pip install -r requirements.txt

# 4. Aplicar migraciones de la base de datos
cd backend
python manage.py makemigrations
python manage.py migrate

# 5. Iniciar el servidor de desarrollo
python manage.py runserver
```

## 📂 Estructura del proyecto

```
WebInformesSekiura/
├── manage.py
├── requirements.txt
├── app/               # Aplicaciones Django personalizadas
├── templates/         # Plantillas HTML (Jinja)
├── static/            # Archivos estáticos (CSS, JS, imágenes)
└── ...
```

## ✅ Notas adicionales

- Las credenciales y configuraciones sensibles deben colocarse en un archivo `.env` (no incluido).
- Accede a la app en `http://127.0.0.1:8000/` tras levantar el servidor.
