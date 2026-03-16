
from flask import Flask, request, redirect, url_for, render_template_string, send_file, session
import sqlite3
import io
import qrcode
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "streetkiosk-secret-key-2026")

DB_NAME = "streetkiosk.db"
TARGET = 5
ADMIN_PIN = os.environ.get("ADMIN_PIN", "2580")


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            stamps INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


init_db()


def cashier_logged_in():
    return session.get("cashier_auth") is True


@app.route("/")
def home():
    conn = get_db()
    customers = conn.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()
    conn.close()

    return render_template_string("""
    <html>
    <body style="font-family:Arial;padding:30px">
        <h1>STREETKIOSK</h1>

        <h2>Νέος πελάτης</h2>
        <form method="post" action="/register">
            <input type="text" name="name" placeholder="Όνομα" required><br><br>
            <input type="text" name="phone" placeholder="Κινητό" required><br><br>
            <button type="submit">Δημιουργία</button>
        </form>

        <h2>Πελάτες</h2>
        {% for c in customers %}
            <p>
                <a href="/customer/{{ c['id'] }}">{{ c["name"] }}</a>
                - {{ c["stamps"] }}/{{ target }}
            </p>
        {% endfor %}

        <p><a href="/cashier-login">Ταμείο</a></p>
    </body>
    </html>
    """, customers=customers, target=TARGET)


@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()

    if not name or not phone:
        return redirect(url_for("home"))

    conn = get_db()

    existing = conn.execute(
        "SELECT id FROM customers WHERE phone = ?",
        (phone,)
    ).fetchone()

    if existing:
        conn.close()
        return redirect(url_for("customer_card", customer_id=existing["id"]))

    cur = conn.execute(
        "INSERT INTO customers (name, phone, stamps) VALUES (?, ?, 0)",
        (name, phone)
    )
    customer_id = cur.lastrowid

    conn.commit()
    conn.close()

    return redirect(url_for("customer_card", customer_id=customer_id))


@app.route("/customer/<int:customer_id>")
def customer_card(customer_id):
    conn = get_db()
    customer = conn.execute(
        "SELECT * FROM customers WHERE id = ?",
        (customer_id,)
    ).fetchone()
    conn.close()

    if not customer:
        return "Ο πελάτης δεν βρέθηκε", 404

    return render_template_string("""
    <html>
    <body style="font-family:Arial;padding:30px;text-align:center">
        <h1>{{ customer["name"] }}</h1>
        <h2>{{ customer["stamps"] }}/{{ target }}</h2>
        <img src="/qr/{{ customer['id'] }}" width="220">
        <p><a href="/customer/{{ customer['id'] }}">Ανανέωση</a></p>
    </body>
    </html>
    """, customer=customer, target=TARGET)


@app.route("/qr/<int:customer_id>")
def qr(customer_id):
    payload = url_for("customer_card", customer_id=customer_id, _external=True)
    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/cashier-login", methods=["GET", "POST"])
def cashier_login():
    if request.method == "POST":
        pin = request.form.get("pin", "")
        if pin == ADMIN_PIN:
            session["cashier_auth"] = True
            return redirect(url_for("scanner"))

    return render_template_string("""
    <html>
    <body style="font-family:Arial;padding:30px;text-align:center">
        <h1>Ταμείο</h1>
        <form method="post">
            <input type="password" name="pin" placeholder="PIN"><br><br>
            <button type="submit">Login</button>
        </form>
    </body>
    </html>
    """)


@app.route("/scanner")
def scanner():
    if not cashier_logged_in():
        return redirect(url_for("cashier_login"))

    return render_template_string("""
    <html>
    <body style="font-family:Arial;padding:30px">
        <h1>Scanner</h1>
        <p>Το scanner άνοιξε σωστά.</p>
        <p><a href="/">Νέα εγγραφή</a></p>
    </body>
    </html>
    """)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

