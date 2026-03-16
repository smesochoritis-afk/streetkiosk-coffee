from flask import Flask, render_template_string, send_file, redirect, url_for, request, session
import qrcode
import io
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "streetkiosk-secret-key-2026")

TARGET = 5
ADMIN_PIN = os.environ.get("ADMIN_PIN", "2580")
DELETE_PASSWORD = os.environ.get("DELETE_PASSWORD", "STRATOS1976!!!")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "STRATOSADMIN2026")

DB_NAME = "streetkiosk.db"
GREECE_TZ = ZoneInfo("Europe/Athens")


def now_str():
    return datetime.now(GREECE_TZ).strftime("%d-%m-%Y %H:%M")


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
        email TEXT,
        stamps INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        action TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


def cashier_logged_in():
    return session.get("cashier_auth") is True


def admin_logged_in():
    return session.get("admin_auth") is True


@app.route("/")
def home():

    conn = get_db()
    customers = conn.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()
    conn.close()

    html = """
    <h1>Streetkiosk</h1>

    <h2>Νέος πελάτης</h2>

    <form method="post" action="/register">
        <input name="name" placeholder="Όνομα" required>
        <input name="phone" placeholder="Κινητό" required>
        <button type="submit">Δημιουργία</button>
    </form>

    <h2>Πελάτες</h2>

    {% for c in customers %}
        <p>
        <a href="/customer/{{c['id']}}">
        {{c["name"]}} ({{c["stamps"]}}/{{target}})
        </a>
        </p>
    {% endfor %}

    <p><a href="/cashier-login">Ταμείο</a></p>
    """

    return render_template_string(html, customers=customers, target=TARGET)


@app.route("/register", methods=["POST"])
def register():

    name = request.form["name"]
    phone = request.form["phone"]

    conn = get_db()

    cur = conn.execute(
        "INSERT INTO customers (name,phone,stamps,created_at) VALUES (?,?,0,?)",
        (name, phone, now_str())
    )

    cid = cur.lastrowid

    conn.execute(
        "INSERT INTO history (customer_id,action,created_at) VALUES (?,?,?)",
        (cid, "Εγγραφή", now_str())
    )

    conn.commit()
    conn.close()

    return redirect(url_for("customer_card", customer_id=cid))


@app.route("/customer/<int:customer_id>")
def customer_card(customer_id):

    conn = get_db()

    customer = conn.execute(
        "SELECT * FROM customers WHERE id=?",
        (customer_id,)
    ).fetchone()

    history = conn.execute(
        "SELECT * FROM history WHERE customer_id=? ORDER BY id DESC",
        (customer_id,)
    ).fetchall()

    conn.close()

    html = """
    <h1>{{customer["name"]}}</h1>

    <h2>{{customer["stamps"]}} / {{target}}</h2>

    <img src="/qr/{{customer_id}}" width="200">

    <h3>Ιστορικό</h3>

    {% for h in history %}
        <p>{{h["action"]}} - {{h["created_at"]}}</p>
    {% endfor %}
    """

    return render_template_string(
        html,
        customer=customer,
        history=history,
        customer_id=customer_id,
        target=TARGET
    )


@app.route("/cashier-login", methods=["GET", "POST"])
def cashier_login():

    if request.method == "POST":

        if request.form["pin"] == ADMIN_PIN:
            session["cashier_auth"] = True
            return redirect("/scanner")

    html = """
    <h1>Ταμείο</h1>

    <form method="post">
        <input name="pin" placeholder="PIN">
        <button>Login</button>
    </form>
    """

    return render_template_string(html)


@app.route("/scanner")
def scanner():

    if not cashier_logged_in():
        return redirect("/cashier-login")

    html = """
    <h1>Scanner</h1>

    <a href="/">Νέος πελάτης</a>

    <p>Σκάναρε QR πελάτη</p>
    """

    return render_template_string(html)


@app.route("/cashier/<int:customer_id>")
def cashier(customer_id):

    if not cashier_logged_in():
        return redirect("/cashier-login")

    conn = get_db()

    customer = conn.execute(
        "SELECT * FROM customers WHERE id=?",
        (customer_id,)
    ).fetchone()

    conn.close()

    html = """
    <h1>{{customer["name"]}}</h1>

    <h2>{{customer["stamps"]}} / {{target}}</h2>

    <form method="post" action="/add/{{customer_id}}">
        <button>+1 Καφές</button>
    </form>

    <p><a href="/scanner">Πίσω</a></p>
    """

    return render_template_string(
        html,
        customer=customer,
        customer_id=customer_id,
        target=TARGET
    )


@app.route("/add/<int:customer_id>", methods=["POST"])
def add_stamp(customer_id):

    conn = get_db()

    customer = conn.execute(
        "SELECT stamps FROM customers WHERE id=?",
        (customer_id,)
    ).fetchone()

    stamps = customer["stamps"] + 1

    if stamps >= TARGET:

        conn.execute(
            "UPDATE customers SET stamps=0 WHERE id=?",
            (customer_id,)
        )

        conn.execute(
            "INSERT INTO history VALUES (NULL,?,?,?)",
            (customer_id, "Δώρο", now_str())
        )

    else:

        conn.execute(
            "UPDATE customers SET stamps=? WHERE id=?",
            (stamps, customer_id)
        )

    conn.execute(
        "INSERT INTO history VALUES (NULL,?,?,?)",
        (customer_id, "+1 καφές", now_str())
    )

    conn.commit()
    conn.close()

    return redirect("/scanner")


@app.route("/qr/<int:customer_id>")
def qr(customer_id):

    payload = url_for("customer_card", customer_id=customer_id, _external=True)

    img = qrcode.make(payload)

    buf = io.BytesIO()

    img.save(buf, format="PNG")

    buf.seek(0)

    return send_file(buf, mimetype="image/png")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
