from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import stripe
import psycopg2

app = Flask(__name__)

# Configuramos CORS
CORS(app)

# Configuramos la conexión a la base de datos PostgreSQL
db_url = os.getenv('DATABASE_URL')  # Obtiene la URL de conexión de Heroku

# Conectar a la base de datos PostgreSQL
try:
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
except Exception as e:
    print(f"Error de conexión a la base de datos: {e}")

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


############## RUTA PARA OBTENER TODOS LOS PRODUCTOS ############################
@app.route('/api/productos', methods=['GET'])
def get_productos():
    try:
        cursor.execute("SELECT * FROM \"gemini-productos\"")
        productos = cursor.fetchall()
        lista_productos = []

        for producto in productos:
            imagen = producto[3]
            if isinstance(imagen, bytes):
                imagen = imagen.decode('utf-8')
            imagen = imagen.strip()

            lista_productos.append({
                'id': producto[0],
                'nombre': producto[1],
                'precio': producto[2],
                'imagen': f'https://gemini-db-82cf11702797.herokuapp.com/uploads/{imagen}',
                'cantidadStock': producto[4],
                'color': producto[5],
                'descripcion': producto[6],
                'material': producto[7],
                'descuento': producto[8],
                'porcentajeDescuento': producto[9],
                'genero': producto[10]
            })

        return jsonify(lista_productos)

    except Exception as e:
        print(f"Error al obtener productos: {e}")
        return jsonify({'mensaje': 'Error al obtener productos'}), 500
    finally:
        cursor.close()
################################################################################


############# RUTA PARA OBTENER UN PRODUCTO POR ID ##############################
@app.route('/api/productos/<int:id>', methods=['GET'])
def get_producto(id):
    try:
        cursor.execute("SELECT * FROM \"gemini-productos\" WHERE id = %s", (id,))
        producto = cursor.fetchone()

        if producto:
            imagen = producto[3]
            if isinstance(imagen, bytes):
                imagen = imagen.decode('utf-8')

            producto_obj = {
                'id': producto[0],
                'nombre': producto[1],
                'precio': producto[2],
                'imagen': f'https://gemini-db-82cf11702797.herokuapp.com/uploads/{imagen}',
                'cantidadStock': producto[4],
                'color': producto[5],
                'descripcion': producto[6],
                'material': producto[7],
                'descuento': producto[8],
                'porcentajeDescuento': producto[9],
                'genero': producto[10]
            }
            return jsonify(producto_obj)
        else:
            return jsonify({'mensaje': 'Producto no encontrado'}), 404

    except Exception as e:
        print(f"Error al obtener el producto: {e}")
        return jsonify({'mensaje': 'Error al obtener el producto'}), 500
    finally:
        cursor.close()
################################################################################


############ RUTA PARA AGREGAR UN NUEVO PRODUCTO ###############################
@app.route('/api/productos/upload', methods=['POST'])
def add_producto():
    # verificamos que se envió una imagen
    imagen = request.files.get('imagen')
    if imagen and imagen.filename and allowed_file(imagen.filename):
        filename = imagen.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        imagen.save(file_path)

        nombre = request.form.get('nombre')  # campo obligatorio
        precio = request.form.get('precio')  # campo obligatorio
        cantidadStock = request.form.get('cantidadStock')  # campo obligatorio
        color = request.form.get('color')  # campo obligatorio
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

            cursor.execute("""
                INSERT INTO \"gemini-productos\" 
                (nombre, precio, imagen, cantidadStock, color, descripcion, material, descuento, porcentajeDescuento, genero) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (nombre, precio, filename, cantidadStock, color, descripcion, material, descuento, porcentajeDescuento, genero))
            conn.commit()

            return jsonify({'mensaje': 'Producto añadida con éxito'}), 201

        except ValueError:
            return jsonify({'mensaje': 'Error en el formato de los datos numéricos (precio, cantidadStock, descuento, porcentajeDescuento)'}), 400
        except Exception as e:
            conn.rollback()
            return jsonify({'mensaje': 'Error al agregar el producto', 'error': str(e)}), 500

    else:
        return jsonify({'mensaje': 'Hubo algún error...'}), 400
################################################################################


############### RUTA PARA ELIMINAR UN PRODUCTO #################################
@app.route('/api/productos/<int:id>', methods=['DELETE'])
def delete_producto(id):
    try:
        # verificamos si la joya existe
        cursor.execute("SELECT * FROM \"gemini-productos\" WHERE id = %s", (id,))
        producto = cursor.fetchone()

        if producto:
            cursor.execute("DELETE FROM \"gemini-productos\" WHERE id = %s", (id,))
            conn.commit()
            return jsonify({'mensaje': 'Producto eliminado con éxito'}), 200
        else:
            return jsonify({'mensaje': 'Producto no encontrado'}), 404

    except Exception as e:
        conn.rollback()
        return jsonify({'mensaje': 'Error al eliminar el producto', 'error': str(e)}), 500
    finally:
        cursor.close()
################################################################################


############## Ruta para subir imágenes ########################################
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


############### RUTA PARA SERVIR ARCHIVOS ESTÁTICOS ###########################
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
################################################################################


############## RUTA PARA COMPRAR UN PRODUCTO ##################################
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
            line_items=data['items'],
            mode='payment',
            success_url='https://gemini-db-82cf11702797.herokuapp.com/success',
            cancel_url='https://gemini-db-82cf11702797.herokuapp.com/cancel',
            metadata={
                'nombre': cliente['nombre'],
                'apellidos': cliente['apellidos'],
                'email': cliente['email'],
                'telefono': cliente['telefono'],
                'direccion': f"{cliente['tipoVia']} {cliente['nombreCalle']} {cliente['numeroCalle']} {cliente['pisoPuerta']}, {cliente['codigoPostal']} {cliente['ciudad']}, {cliente['provincia']}, {cliente['pais']}"
            }
        )

        return jsonify({'id': session.id})

    except Exception as e:
        print(f"Error en la creación de sesión de pago: {e}")
        return jsonify({'error': str(e)}), 500
################################################################################


# Levantamos el servidor
if __name__ == '__main__':
    app.run(debug=True)
