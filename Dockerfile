# Usa una imagen oficial de Python
FROM python:3.11

# Define el directorio de trabajo en el contenedor
WORKDIR /app

# Copia los archivos necesarios
COPY requirements.txt requirements.txt

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de la aplicación
COPY . .

# Comando por defecto
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
