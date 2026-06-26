import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='../templates')
app.secret_key = os.getenv("SECRET_KEY", "dev-fallback-key-99X")

def get_db():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        db_url = "postgresql://postgres:postgres@localhost:5432/arusaku"
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)

def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    description TEXT NOT NULL,
                    amount BIGINT NOT NULL,
                    type VARCHAR(10) NOT NULL,
                    category VARCHAR(30) NOT NULL,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()

try:
    init_db()
except Exception as e:
    print(f"[ERROR] Database initialization failed: {e}", file=sys.stderr)

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return f"Dashboard Arusaku - Welcome, {session['username']}"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            return render_template('login.html', error="Semua field wajib diisi.")
            
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cur.fetchone()
                
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
            
        return render_template('login.html', error="Username atau password salah.")
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)