from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = '3,1415926535'

# user hardcoded
USERS = {
    "eka.adrianti": {"password": "194746", "role": "admin"},
    "kamar7.1": {"password": "smpitassyifa", "role": "viewer"},
}

# --------- Fungsi DB ---------
def get_db_path():
    return 'database_global.db'

def init_db():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        with sqlite3.connect(db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS transaksi (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                tanggal TEXT NOT NULL,
                                kategori TEXT NOT NULL,
                                jumlah INTEGER NOT NULL,
                                keterangan TEXT NOT NULL
                            )''')
            conn.commit()

def query_db(query, args=(), one=False):
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(query, args)
        result = cur.fetchall()
        conn.commit()
        return (result[0] if result else None) if one else result

def insert_transaksi(kategori, jumlah, keterangan):
    db_path = get_db_path()
    tanggal = datetime.now().strftime('%d/%m/%Y')
    query_db('INSERT INTO transaksi (tanggal, kategori, jumlah, keterangan) VALUES (?, ?, ?, ?)',
             (tanggal, kategori, jumlah, keterangan))

def get_saldo():
    rows = query_db('SELECT kategori, jumlah FROM transaksi')
    saldo = 0
    for r in rows:
        if r['kategori'] == 'Pemasukan':
            saldo += r['jumlah']
        else:
            saldo -= r['jumlah']
    return saldo

# --------- ROUTES ---------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = USERS.get(username)

        if user and user['password'] == password:
            session['logged_in'] = True
            session['username'] = username
            session['role'] = user['role']
            init_db()
            return redirect(url_for('index'))
        else:
            flash("Login gagal. Username atau password salah.", "error")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # Pagination setup
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    offset = (page - 1) * per_page

    total_rows = query_db("SELECT COUNT(*) as count FROM transaksi", one=True)['count']
    total_pages = (total_rows + per_page - 1) // per_page

    transaksi = query_db("SELECT * FROM transaksi ORDER BY id DESC LIMIT ? OFFSET ?", (per_page, offset))
    saldo = get_saldo()

    latest_income = query_db("SELECT * FROM transaksi WHERE kategori = 'Pemasukan' ORDER BY id DESC LIMIT 1", one=True)
    latest_expense = query_db("SELECT * FROM transaksi WHERE kategori = 'Pengeluaran' ORDER BY id DESC LIMIT 1", one=True)

    return render_template('index.html',
        data=transaksi,
        saldo=saldo,
        latest_income=latest_income,
        latest_expense=latest_expense,
        username=session['username'],
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )

@app.route('/tambah', methods=['POST'])
def tambah():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if session.get('role') != 'admin':
        flash("Anda tidak memiliki izin untuk menambahkan data.", "error")
        return redirect(url_for('index'))

    jumlah = request.form.get("jumlah")
    keterangan = request.form.get("keterangan")
    kategori = request.form.get("kategori")

    if not jumlah or not keterangan:
        flash("Form tidak boleh kosong!", "error")
        return redirect(url_for('index'))

    try:
        jumlah = int(jumlah.replace('.', '').replace(',', ''))  # convert format rupiah
    except:
        flash("Format jumlah tidak valid", "error")
        return redirect(url_for('index'))

    insert_transaksi(kategori, jumlah, keterangan)
    return redirect(url_for('index'))

@app.route('/export')
def export():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    data = query_db("SELECT * FROM transaksi ORDER BY id DESC")
    saldo = get_saldo()

    def generate():
        yield 'Tanggal;Kategori;Jumlah;Keterangan\n'
        for row in data:
            line = f"{row['tanggal']};{row['kategori']};{row['jumlah']};{row['keterangan']}\n"
            yield line
        yield '\nTOTAL SALDO;;Rp {:,}\n'.format(saldo)

    filename = f"transaksi_{session['username']}.csv"
    return Response(generate(), mimetype='text/csv',
                    headers={"Content-Disposition": f"attachment;filename={filename}"})


# --------- MAIN ---------
if __name__ == "__main__":
    app.run(debug=True)
