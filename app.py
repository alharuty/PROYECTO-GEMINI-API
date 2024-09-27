from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_mysqldb import MySQL
import os
import stripe

app = Flask(__name__)

from flask import Flask
from flask_cors import CORS

app = Flask(__name__)

# Configuración de CORS
CORS(app, resources={r"/api/*": {
    "origins": "http://localhost:3000",
    "supports_credentials": True
}})

stripe.api_key = "sk_test_51Q290kH0Oxn0trnELbauIxm7bQHVujWZTtRA1F5QWcxG0iOnhrkBzd6OZ3CacW7wJ9Cgfz2RJBSRxZTS3EtfThya00K9sMQ5QJ"


# Configuración de MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Trikitiki22.'
app.config['MYSQL_DB'] = 'gemini-db'

mysql = MySQL(app)

# Configuración del directorio para almacenar imágenes
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Crear el directorio 'uploads' si no existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Tipos de archivo permitidos
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ruta para obtener todas las joyas
@app.route('/api/joyas', methods=['GET'])
def get_joyas():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM `gemini-joyas`")
    joyas = cur.fetchall()
    joyas_list = []

    for joya in joyas:
        imagen = joya[3]
        if isinstance(imagen, bytes):
            imagen = imagen.decode('utf-8')  # Convertir bytes a cadena de texto
        imagen = imagen.strip()  # Eliminar espacios en blanco

        joyas_list.append({
            'id': joya[0],
            'nombre': joya[1],
            'precio': joya[2],
            'imagen': f'http://127.0.0.1:5000/uploads/{imagen}',  # Construir URL correctamente
            'cantidadStock': joya[4],
            'color': joya[5]
        })

    cur.close()
    return jsonify(joyas_list)


# Ruta para obtener una joya por ID
@app.route('/api/joyas/<int:id>', methods=['GET'])
def get_joya(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM `gemini-joyas` WHERE id = %s", (id,))
    joya = cur.fetchone()

    if joya:
        # Convertir el nombre del archivo a cadena si es necesario
        imagen = joya[3]
        if isinstance(imagen, bytes):
            imagen = imagen.decode('utf-8')  # Convertir bytes a cadena de texto
        
        joya_obj = {
            'id': joya[0],
            'nombre': joya[1],
            'precio': joya[2],
            'imagen': f'http://127.0.0.1:5000/uploads/{imagen}',
            'cantidadStock': joya[4],
            'color': joya[5]
        }
        cur.close()
        return jsonify(joya_obj)
    else:
        cur.close()
        return jsonify({'mensaje': 'Joya no encontrada'}), 404


# Ruta para agregar una nueva joya
@app.route('/api/joyas/upload', methods=['POST'])
def add_joya():
    # Verificar que se envió una imagen
    imagen = request.files.get('imagen')
    if imagen and imagen.filename and allowed_file(imagen.filename):
        filename = imagen.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        imagen.save(file_path)

        nombre = request.form.get('nombre')
        precio = request.form.get('precio')
        cantidadStock = request.form.get('cantidadStock')
        color = request.form.get('color')

        if not all([nombre, precio, cantidadStock, color]):
            return jsonify({'mensaje': 'Faltan datos de la joya'}), 400

        # Insertar la joya en la base de datos
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO `gemini-joyas` (nombre, precio, imagen, cantidadStock, color) 
            VALUES (%s, %s, %s, %s, %s)
        """, (nombre, float(precio), filename, int(cantidadStock), color))
        mysql.connection.commit()
        cur.close()

        return jsonify({'mensaje': 'Joya añadida con éxito'}), 201
    else:
        return jsonify({'mensaje': 'Imagen no válida o formato no permitido'}), 400

# Ruta para eliminar una joya por ID
@app.route('/api/joyas/<int:id>', methods=['DELETE'])
def delete_joya(id):
    cur = mysql.connection.cursor()
    
    # Verificar si la joya existe
    cur.execute("SELECT * FROM `gemini-joyas` WHERE id = %s", (id,))
    joya = cur.fetchone()
    
    if joya:
        # Eliminar la joya
        cur.execute("DELETE FROM `gemini-joyas` WHERE id = %s", (id,))
        mysql.connection.commit()
        cur.close()
        return jsonify({'mensaje': 'Joya eliminada con éxito'}), 200
    else:
        cur.close()
        return jsonify({'mensaje': 'Joya no encontrada'}), 404
    


# Ruta para subir imágenes
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'mensaje': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'mensaje': 'No se seleccionó ningún archivo'}), 400
    
    if file and allowed_file(file.filename):
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        return jsonify({'mensaje': 'Archivo subido con éxito', 'file_url': f'{request.host_url}uploads/{filename}'}), 201
    else:
        return jsonify({'mensaje': 'Formato de archivo no permitido'}), 400


# Ruta para servir archivos estáticos
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/test-connection', methods=['GET'])
def test_connection():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT 1")
        cur.close()
        return jsonify({"mensaje": "Conexión exitosa a MySQL"}), 200
    except Exception as e:
        return jsonify({"mensaje": f"Error al conectar: {str(e)}"}), 500
    

# Ruta para agregar un nuevo modelo de producto sin asociarlo a una joya específica
@app.route('/api/modelos', methods=['POST'])
def add_modelo():
    try:
        data = request.json  # Asegúrate de que el frontend está enviando datos en formato JSON

        # Obtén los datos del cuerpo de la solicitud
        id_nombre_modelo = data.get('id_nombre_modelo')
        nombre_modelo = data.get('nombre_modelo')
        precio_modelo = data.get('precio_modelo')

        # Si id_nombre_modelo no es necesario, elimínalo
        # id_nombre_modelo = data.get('id_nombre_modelo') 

        # Validar que los datos requeridos estén presentes
        if not nombre_modelo or not precio_modelo:
            return jsonify({'mensaje': 'El nombre y el precio del modelo son requeridos'}), 400

        # Insertar el nuevo modelo en la base de datos
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO `nombre-modelos` (id_nombre_modelo, nombre_modelo, precio_modelo)
            VALUES (%s, %s, %s)
        """, (id_nombre_modelo, nombre_modelo, precio_modelo))
        mysql.connection.commit()
        cur.close()

        return jsonify({'mensaje': 'Modelo añadido con éxito'}), 201

    except Exception as e:
        print(f"Error en add_modelo: {str(e)}")  # Esto imprimirá el error exacto en la consola
        return jsonify({'mensaje': 'Error interno del servidor', 'error': str(e)}), 500

# Ruta para obtener todos los modelos de productos
@app.route('/api/modelos', methods=['GET'])
def get_modelos():
    try:
        # Realiza la consulta a la base de datos para obtener todos los modelos
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM `nombre-modelos`")
        modelos = cur.fetchall()  # Recuperar todos los registros

        # Crear una lista para almacenar los modelos en formato JSON
        modelos_list = []
        for modelo in modelos:
            modelos_list.append({
                'id_nombre_modelo': modelo[0],
                'nombre_modelo': modelo[1],
                'precio_modelo': modelo[2]
            })

        cur.close()

        # Devolver la lista de modelos en formato JSON
        return jsonify(modelos_list), 200

    except Exception as e:
        print(f"Error en get_modelos: {str(e)}")  # Imprime el error en la consola
        return jsonify({'mensaje': 'Error interno del servidor', 'error': str(e)}), 500

@app.route('/checkout', methods=['POST'])
def checkout():
    print("Petición recibida en /checkout")
    try:
        data = request.get_json()

        # Verificar si se enviaron los items y los datos del cliente
        if 'items' not in data or not data['items']:
            return jsonify({'error': 'No se enviaron productos para el checkout'}), 400
        if 'cliente' not in data:
            return jsonify({'error': 'No se enviaron datos del cliente'}), 400

        cliente = data['cliente']

        print("Creando sesión de pago con metadata:", {
            'nombre': cliente['nombre'],
            'apellidos': cliente['apellidos'],
            'email': cliente['email'],
            'telefono': cliente['telefono'],
            'direccion': f"{cliente['tipoVia']} {cliente['nombreCalle']} {cliente['numeroCalle']} {cliente['pisoPuerta']}, {cliente['codigoPostal']} {cliente['ciudad']}, {cliente['provincia']}, {cliente['pais']}"
        })

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {'name': item['nombre']},
                    'unit_amount': int(item['precio'] * 100),
                },
                'cantidadStock': item['cantidadStock'],
            } for item in data['items']],
            mode='payment',
            success_url='http://localhost:3000/pago-completado',
            cancel_url='http://localhost:3000/pago-cancelado',
            payment_intent_data={
                'metadata': {
                    'nombre': cliente['nombre'],
                    'apellidos': cliente['apellidos'],
                    'email': cliente['email'],
                    'telefono': cliente['telefono'],
                    'direccion': f"{cliente['tipoVia']} {cliente['nombreCalle']} {cliente['numeroCalle']} {cliente['pisoPuerta']}, {cliente['codigoPostal']} {cliente['ciudad']}, {cliente['provincia']}, {cliente['pais']}"
                }
            }
        )
        return jsonify({'url': session.url})

    except stripe.error.StripeError as e:
        return jsonify({'error': f'Error de Stripe: {str(e)}'}), 500
    except Exception as e:
        print(f"Error en el checkout: {e}")
        return jsonify({'error': f'Ocurrió un error: {str(e)}'}), 500


# Ruta para obtener todas las secciones
@app.route('/api/secciones-navegador', methods=['GET'])
def get_secciones():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM `secciones-navegador`")
    secciones = cur.fetchall()
    secciones_list = []

    for seccion in secciones:
        imagen = seccion[2]
        if isinstance(imagen, bytes):
            imagen = imagen.decode('utf-8')  # Convertir bytes a cadena de texto
        imagen = imagen.strip()  # Eliminar espacios en blanco

        secciones_list.append({
            'id': seccion[0],
            'nombre_seccion': seccion[1],
            'imagen_seccion': f'http://127.0.0.1:5000/{imagen}',  # Construir URL correctamente
        })

    cur.close()
    return jsonify(secciones_list)

@app.route('/api/secciones-navegador', methods=['POST'])
def create_seccion():
    try:
        cur = mysql.connection.cursor()
        
        data = request.get_json()
        id = data.get('id')
        nombre_seccion = data.get('nombre_seccion')
        imagen_seccion = data.get('imagen_seccion')

        # Verificar que todos los campos necesarios estén presentes
        if not all([id, nombre_seccion, imagen_seccion]):
            return jsonify({'error': 'Faltan campos requeridos'}), 400

        ruta_imagen = f'{imagen_seccion}'  # asumiendo que la imagen está en la carpeta uploads


        cur.execute(
            "INSERT INTO `secciones-navegador` (id, nombre_seccion, imagen_seccion) VALUES (%s, %s, %s)",
            (id, nombre_seccion, ruta_imagen)
        )
        mysql.connection.commit()
        cur.close()

        return jsonify({'message': 'Sección creada exitosamente'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS,DELETE')
    return response

if __name__ == '__main__':
    app.run(debug=True)



# Ejemplo de GET o POST de /api/secciones-navegador
# [
#     {
#         "id": 1,
#         "imagen_seccion": "http://127.0.0.1:5000/uploads/uploads/Pendientes.png",
#         "nombre_seccion": "Pendientes"
#     },
#     {
#         "id": 2,
#         "imagen_seccion": "http://127.0.0.1:5000/uploads/uploads/Cuadro2.jpg",
#         "nombre_seccion": "Cuadros"
#     },
#     {
#         "id": 3,
#         "imagen_seccion": "http://127.0.0.1:5000/uploads/uploads/PlatoPostres.jpg",
#         "nombre_seccion": "Otros"
#     }
# ]