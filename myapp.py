from flask import Flask, render_template, session, request, redirect, url_for, flash
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import os

# init main app
app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# kunci rahasia agar session bisa berjalan
app.secret_key = '!@#$%'

# database config
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "db_tokopakaian"

# init mysql
mysql = MySQL(app)

@app.route('/', methods=['GET', 'POST'])
def login():
    user_type = "user" 
    if request.method == 'POST' and 'inpEmail' in request.form and 'inpPass' in request.form:
        email = request.form['inpEmail']
        passwd = request.form['inpPass']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, passwd))
        result = cur.fetchone()
        cur.close()

        if result:
            user_type = result[4]

            if user_type == 'user':
                session['is_logged_in'] = True
                session['username'] = result[1]
                if 'cart' not in session:
                    session['cart'] = []
                return redirect(url_for('home'))
                
            elif user_type == 'admin':
                session['is_logged_in_admin'] = True
                session['username'] = result[1]
                return redirect(url_for('admin'))
        else:
            return render_template('login.html')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        regusn = request.form['inpUsn']
        regmail = request.form['inpEmail']
        regpasswd = request.form['inpPass']
        regpasswd2 = request.form['inpPass2']
        if regpasswd == regpasswd2:
            mycursor = mysql.connection.cursor()
            query = "INSERT INTO users (username, password, email, user_type) VALUES (%s, %s, %s, 'user')"
            mycursor.execute(query, (regusn, regpasswd, regmail))
            mysql.connection.commit()
            return redirect(url_for('login'))
        else:
            return "email tidak valid"
    else:
        return render_template('register.html')

def get_some_product_data():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM produk ORDER BY RAND() LIMIT 1")
        product = cur.fetchone()
        cur.close()
        return product
    except Exception as e:
        print(f"Error fetching product data: {str(e)}")
        return None

@app.route('/home')
def home():
    if 'is_logged_in' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users")
        data = cur.fetchall()
        cur.close()

        # Get some product data or set to None if there's an error
        product = get_some_product_data()

        return render_template('users/home.html', users=data, product=product)
    else:
        return redirect(url_for('login'))


@app.route('/product')
def product():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM produk')
    products = cur.fetchall()
    cur.close()
    
    return render_template('users/product.html', products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM produk WHERE id = %s', (product_id,))
    product = cur.fetchone()
    cur.close()

    if product:
        return render_template('users/product_detail.html', product=product)
    else:
        return render_template('error_page.html', message='Product not found', product=None)


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = []

    cur = mysql.connection.cursor()
    cur.execute("SELECT * from produk where id = %s", (int(product_id),))
    product = cur.fetchone()
        
    if product not in session['cart']:
        
        session['cart'].append(product)
        flash('Product added to cart successfully!', 'success')

    return redirect(url_for('product')) 

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    if 'cart' in session and product_id in session['cart']:
        session['cart'].remove(product_id)
        flash('Product removed from cart successfully!', 'success')
        
    return redirect(url_for('product'))  

@app.route('/checkout')
def checkout():
    if 'is_logged_in' in session:
        cur = mysql.connection.cursor()
        product_ids = []
        for product in session['cart']:
            product_ids.append(product[0])
            
        
        cur.execute('SELECT * FROM produk WHERE id IN ({})'.format(','.join(map(str, product_ids))))
        products_in_cart = cur.fetchall()
        cur.close()
        return render_template('users/checkout.html', products_in_cart=products_in_cart)
    else:
        return redirect(url_for('login'))

@app.route('/process_checkout', methods=['POST'])
def process_checkout():
    try:
        # Your existing code for processing checkout

        print("Checkout successful!")  # Add this line for debugging

        session.pop('cart', None)
        flash('Checkout successful!', 'success')
        return redirect(url_for('home'))

    except Exception as e:
        print(f"Checkout error: {str(e)}")
        flash('An error occurred during checkout. Please try again.', 'error')
        return redirect(url_for('checkout'))



@app.route('/about')
def about():
    return render_template('users/about.html')

@app.route('/contact')
def contact():
    return render_template('users/contact.html')

@app.route('/logout')
def logout():
    session.pop('is_logged_in', None)
    session.pop('is_logged_in_admin', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/admin')
def admin():
    if 'is_logged_in_admin' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users")
        users = cur.fetchall()
        cur.close()
        return render_template('admin/admin_page.html', users=users)
    else:
        return redirect(url_for('login'))

# CRUD admin product
@app.route('/admin_produk')
def admin_produk():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM produk')
    data = cur.fetchall()
    cur.close()
    return render_template('admin/admin_produk.html', products=data)

@app.route('/add', methods=['POST'])
def add_produk():
    if request.method == 'POST':
        product = request.form
        file = request.files['file_gambar']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            cur = mysql.connection.cursor()
            cur.execute('''
                INSERT INTO produk (no_artikel, nama, deskripsi, harga, size, file_gambar)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (product['no_artikel'], product['nama'], product['deskripsi'], product['harga'], product['size'], filename))
            mysql.connection.commit()
            cur.close()
            
            return redirect(url_for('admin_produk'))
    return "Failed to add product"
        
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/edit_produk/<int:id>', methods=['GET', 'POST'])
def edit_produk(id):
    print("called")
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM produk WHERE id = %s', (id,))
    product = cur.fetchone()
    cur.close()
    

    if request.method == 'POST':
        edited_product = request.form
        file = request.files['file_gambar']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            cur = mysql.connection.cursor()
            cur.execute('''
                UPDATE produk
                SET no_artikel=%s, nama=%s, deskripsi=%s, harga=%s, size=%s, file_gambar=%s
                WHERE id=%s
            ''', (edited_product['no_artikel'], edited_product['nama'], edited_product['deskripsi'],
                  edited_product['harga'], edited_product['size'], filename, id))
            mysql.connection.commit()
            cur.close()

            flash('Product updated successfully!', 'success')
            return redirect(url_for('admin_produk'))

    return render_template('admin/edit_product.html', product=product)

@app.route('/delete/<int:id>')
def delete_produk(id):
    cur = mysql.connection.cursor()
    cur.execute('DELETE FROM produk WHERE id = %s', (id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('admin_produk'))


if __name__ == '__main__':
    app.run(debug=True)
