# Usa una imagen oficial de Python
FROM python:3.11

# Define el directorio de trabajo en el contenedor
WORKDIR /app

# Copia los archivos necesarios
COPY requirements.txt .

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de la aplicación
COPY . .

# Establece variables de entorno necesarias para Flask
ENV FLASK_APP=app.py
ENV FLASK_ENV=development


# Comando por defecto para ejecutar la app
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
