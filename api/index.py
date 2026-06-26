import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import DictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='../templates')
app.secret_key = os.environ.get('SECRET_KEY', 'arusaku_secret_key_123')

# Helper untuk koneksi database
def get_db_connection():
    # Menggunakan DATABASE_URL bawaan Vercel Postgres / Neon
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        # Fallback lokal jika kamu setup .env nanti
        db_url = "postgresql://postgres:password@localhost:5432/finance_db"
    
    conn = psycopg2.connect(db_url, cursor_factory=DictCursor)
    return conn

# 1. HOMEPAGE (DASHBOARD FINANCE)
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    return render_template('index.html', username=session['username'])

# 2. FITUR REGISTER (BUAT AKUN)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username').strip().lower()
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        
        if not username or not email or not password:
            flash('Semua kolom wajib diisi!', 'error')
            return render_template('register.html')

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # Cek apakah username atau email sudah terdaftar
            cur.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
            if cur.fetchone():
                flash('Username atau Email sudah terdaftar!', 'error')
                return render_template('register.html')

            # Simpan user baru ke database
            cur.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                (username, email, hashed_password)
            )
            conn.commit()
            flash('Akun berhasil dibuat! Silakan login.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            conn.rollback()
            flash('Terjadi kesalahan sistem. Coba lagi nanti.', 'error')
        finally:
            cur.close()
            conn.close()

    return render_template('register.html')

# 3. FITUR LOGIN (BISA USERNAME / EMAIL)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        login_input = request.form.get('username').strip().lower()
        password = request.form.get('password')

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            # Cari berdasarkan username ATAU email
            cur.execute("SELECT * FROM users WHERE username = %s OR email = %s", (login_input, login_input))
            user = cur.fetchone()

            if user and check_password_hash(user['password'], password):
                # Set session user
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['email'] = user['email']
                return redirect(url_for('index'))
            else:
                flash('Username/Email atau Password salah!', 'error')
        except Exception as e:
            flash('Gagal terhubung ke server database.', 'error')
        finally:
            cur.close()
            conn.close()

    return render_template('login.html')

import os
import requests  # <-- Pastikan sudah ada 'requests' di bagian atas file kamu
from flask import redirect, url_for, session, flash, request

# # 4. FITUR GOOGLE LOGIN (REAL ROUTE)
@app.route('/login/google')
def login_google():
    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    if not client_id:
        return "Error: GOOGLE_CLIENT_ID belum disetting di Environment Variables Vercel!"
        
    # Alamat urutan setelah user berhasil login di Google
    redirect_uri = "https://arusaku.vercel.app/login/google/callback"
    scope = "openid email profile"
    
    # Membuat URL otomatis untuk dilempar ke halaman login Google
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={scope}"
    )
    return redirect(google_auth_url)

@app.route('/login/google/callback')
def google_callback():
    code = request.args.get("code")
    if not code:
        return "Gagal mendapatkan kode otorisasi dari Google.", 400
        
    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
    redirect_uri = "https://arusaku.vercel.app/login/google/callback"
    
    # 1. Tukarkan 'code' dari Google menjadi Access Token resmi
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    token_r = requests.post(token_url, data=token_data)
    token_json = token_r.json()
    access_token = token_json.get("access_token")
    
    if not access_token:
        return f"Gagal menukar token: {token_json}", 400
        
    # 2. Ambil data profil/email user menggunakan Access Token tersebut
    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    userinfo_r = requests.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
    user_info = userinfo_r.json()
    
    # 3. Simpan data user ke Session Flask (tanda user sudah berhasil masuk)
    session['logged_in'] = True
    session['username'] = user_info.get("name")
    session['email'] = user_info.get("email")
    
    flash(f"Selamat datang, {session['username']}!", "success")
    return redirect(url_for('index'))  # Melempar user ke halaman utama (Dashboard)
    session.clear()
    return redirect(url_for('login'))
