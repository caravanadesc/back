from flask import Flask, request, jsonify, send_from_directory
from flask_mail import Mail
from flask_cors import CORS
from routes.proyecto import bp
from routes.areainvestigacion import bp_area as areainvestigacion_bp
from routes.usuarios import bp as usuarios_bp
from db import get_connection

app = Flask(__name__)
CORS(app)

# Configuración de Flask-Mail aquí si la usas
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'uxlabti@unca.edu.mx'
app.config['MAIL_PASSWORD'] = 'uram xkfx ejsi gqqf'
app.config['MAIL_DEFAULT_SENDER'] = 'uxlabti@unca.edu.mx'
mail = Mail(app)

app.register_blueprint(bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(areainvestigacion_bp)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('src/uploads', filename)

if __name__ == '__main__':
    app.run(debug=True)
