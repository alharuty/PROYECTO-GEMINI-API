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

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# RUTA PARA OBTENER TODOS LOS PRODUCTOS
@app.route('/api/productos', methods=['GET'])
def get_productos():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM `gemini-productos`")
    productos = cur.fetchall()
    lista_productos = []

    for producto in productos:
        imagen = producto[3]
        if isinstance(imagen, bytes):
            imagen = imagen.decode('utf-8')  # Convertir bytes a cadena de texto
        imagen = imagen.strip()

        lista_productos.append({
            'id': producto[0],
            'nombre': producto[1],
            'precio': producto[2],
            'imagen': f'http://127.0.0.1:5000/uploads/{imagen}',
            'cantidadStock': producto[4],
            'color': producto[5],
            'descripcion': producto[6],
            'material': producto[7],
            'descuento': producto[8],
            'porcentajeDescuento': producto[9],
            'genero': producto[10]
        })

    cur.close()
    return jsonify(lista_productos)
################################################################################


# RUTA PARA OBTENER UN PRODUCTO POR ID
@app.route('/api/productos/<int:id>', methods=['GET'])
def get_producto(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM `gemini-productos` WHERE id = %s", (id,))
    producto = cur.fetchone()

    if producto:
        # Convertir el nombre del archivo a cadena si es necesario
        imagen = producto[3]
        if isinstance(imagen, bytes):
            imagen = imagen.decode('utf-8')  # Convertir bytes a cadena de texto
        
        producto_obj = {
            'id': producto[0],
            'nombre': producto[1],
            'precio': producto[2],
            'imagen': f'http://127.0.0.1:5000/uploads/{imagen}',
            'cantidadStock': producto[4],
            'color': producto[5],
            'descripcion': producto[6],
            'material': producto[7],
            'descuento': producto[8],
            'porcentajeDescuento': producto[9],
            'genero': producto[10]
        }
        cur.close()
        return jsonify(producto_obj)
    else:
        cur.close()
        return jsonify({'mensaje': 'Producto no encontrado'}), 404
################################################################################


# RUTA PARA AGREGAR UN NUEVO PRODUCTO
@app.route('/api/productos/upload', methods=['POST'])
def add_producto():
    # verificamos que se envió una imagen
    imagen = request.files.get('imagen')
    if imagen and imagen.filename and allowed_file(imagen.filename):
        filename = imagen.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        imagen.save(file_path)

        nombre = request.form.get('nombre')
        precio = request.form.get('precio')
        cantidadStock = request.form.get('cantidadStock')
        color = request.form.get('color')
        descripcion = request.form.get('descripcion')  # campo opcional
        material = request.form.get('material')  # campo obligatorio
        descuento = request.form.get('descuento', 0)  # por defecto 0 (sin descuento)
        porcentajeDescuento = request.form.get('porcentajeDescuento', 0)  # por defecto 0
        genero = request.form.get('genero')  # campo obligatorio

        if not all([nombre, precio, cantidadStock, color, material, genero]):
            return jsonify({'mensaje': 'Faltan datos obligatorios del producto'}), 400

        try:
            precio = float(precio)
            cantidadStock = int(cantidadStock)
            descuento = int(descuento)
            porcentajeDescuento = int(porcentajeDescuento)

            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO `gemini-productos` 
                (nombre, precio, imagen, cantidadStock, color, descripcion, material, descuento, porcentajeDescuento, genero) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (nombre, precio, filename, cantidadStock, color, descripcion, material, descuento, porcentajeDescuento, genero))
            mysql.connection.commit()
            cur.close()

            return jsonify({'mensaje': 'Producto añadida con éxito'}), 201

        except ValueError:
            return jsonify({'mensaje': 'Error en el formato de los datos numéricos (precio, cantidadStock, descuento, porcentajeDescuento)'}), 400

    else:
        return jsonify({'mensaje': 'Hubo algun error...'}), 400
################################################################################


# RUTA PARA ELIMINAR UN PRODUCTO
@app.route('/api/productos/<int:id>', methods=['DELETE'])
def delete_producto(id):
    cur = mysql.connection.cursor()
    
    # verificamos si la joya existe
    cur.execute("SELECT * FROM `gemini-productos` WHERE id = %s", (id,))
    producto = cur.fetchone()
    
    if producto:
        cur.execute("DELETE FROM `gemini-productos` WHERE id = %s", (id,))
        mysql.connection.commit()
        cur.close()
        return jsonify({'mensaje': 'Producto eliminado con éxito'}), 200
    else:
        cur.close()
        return jsonify({'mensaje': 'Producto no encontrado'}), 404
################################################################################
    


# Ruta para subir imágenes
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'mensaje': 'No se eligió ninguna imagen'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'mensaje': 'No se seleccionó ningún archivo'}), 400
    
    if file and allowed_file(file.filename):
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        return jsonify({'mensaje': 'Imagen subida con éxito', 'file_url': f'{request.host_url}uploads/{filename}'}), 201
    else:
        return jsonify({'mensaje': 'Formato de archivo no permitido'}), 400
################################################################################


# RUTA PARA SERVIR ARCHIVOS ESTÁTICOS
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
################################################################################


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
    

# RUTA PARA COMPRAR UN PRODUCTO
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
                'quantity': item['cantidadStock'],
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
################################################################################


## RUTA PARA CREAR UN nuevo genero
@app.route('/api/generos', methods=['POST'])
def create_genero():
    try:
        cur = mysql.connection.cursor()
        
        # Verificar que se ha subido una imagen
        if 'imagen_genero' not in request.files:
            return jsonify({'error': 'No se ha subido ninguna imagen'}), 400
        
        imagen_genero = request.files['imagen_genero']  # Obtener el archivo de imagen
        
        # Obtener el id y el nombre desde los datos de formulario
        id = request.form.get('id')
        nombre_genero = request.form.get('nombre_genero')

        if not all([id, nombre_genero, imagen_genero]):
            return jsonify({'error': 'Faltan campos requeridos'}), 400

        # Guardar la imagen en el servidor
        ruta_imagen = os.path.join(app.config['UPLOAD_FOLDER'], imagen_genero.filename)
        imagen_genero.save(ruta_imagen)  # Guardar el archivo en el servidor

        # Insertar en la base de datos
        cur.execute(
            "INSERT INTO `generos` (id, nombre_genero, imagen_genero) VALUES (%s, %s, %s)",
            (id, nombre_genero, ruta_imagen)
        )
        mysql.connection.commit()
        cur.close()

        return jsonify({'message': 'Género creado exitosamente'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500
################################################################################


# RUTA PARA OBTENER TODAS LAS GÉNEROS QUE TENEMOS
@app.route('/api/generos', methods=['GET'])
def get_generos():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM `generos`")
    generos = cur.fetchall()
    generos_list = []

    for genero in generos:
        imagen = genero[2]
        if isinstance(imagen, bytes):
            imagen = imagen.decode('utf-8')  # Convertir bytes a cadena de texto
        imagen = imagen.strip()  # Eliminar espacios en blanco

        generos_list.append({
            'id': genero[0],
            'nombre_genero': genero[1],
            'imagen_genero': f'http://127.0.0.1:5000/{imagen}',
        })

    cur.close()
    return jsonify(generos_list)
################################################################################


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000' )
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS,DELETE')
    return response

if __name__ == '__main__':
    app.run(debug=True)
