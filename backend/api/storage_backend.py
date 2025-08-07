from django.core.files.storage import FileSystemStorage

class OverwriteStorage(FileSystemStorage):
    """Sobrescribe el archivo si ya existe."""
    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            self.delete(name)
        return name