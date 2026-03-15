from flask import Flask, render_template_string, send_file, redirect, url_for, request, session
import qrcode
import io
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "streetkiosk-secret-key-2026")

TARGET = 5
ADMIN_PIN = os.environ.get("ADMIN_PIN", "2580")
DELETE_PASSWORD = os.environ.get("DELETE_PASSWORD", "STRATOS1976!!!")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "STRATOSADMIN2026")
DB_NAME = "streetkiosk.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def now_str():
    return datetime.now().strftime("%d-%m-%Y %H:%M")


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            email TEXT UNIQUE,
            stamps INTEGER NOT NULL DEFAULT 0,
            terms_accepted INTEGER NOT NULL DEFAULT 0,
            marketing_consent INTEGER NOT NULL DEFAULT 0,
            terms_accepted_at TEXT,
            marketing_consent_at TEXT,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
    """)

    conn.commit()
    conn.close()


init_db()


def cashier_logged_in():
    return session.get("cashier_auth") is True


def admin_logged_in():
    return session.get("admin_auth") is True


REGISTER_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>STREETKIOSK</title>
<style>
body{
    font-family:Arial,sans-serif;
    background:#f4f4f4;
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:100vh;
    margin:0;
    padding:20px
}
.card{
    background:white;
    width:400px;
    padding:30px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15)
}
h1{text-align:center;margin-top:0}
p{text-align:center;color:#666}
input{
    width:100%;
    box-sizing:border-box;
    padding:12px;
    margin-bottom:12px;
    border:1px solid #ccc;
    border-radius:10px;
    font-size:16px
}
button{
    width:100%;
    padding:14px;
    border:none;
    border-radius:10px;
    background:#222;
    color:white;
    font-size:16px;
    cursor:pointer
}
.list{
    margin-top:20px;
    border-top:1px solid #eee;
    padding-top:12px
}
.customer{
    padding:10px;
    background:#fafafa;
    border-radius:10px;
    margin-bottom:8px
}
.customer a{
    text-decoration:none;
    color:#222;
    font-weight:bold
}
.small{font-size:13px;color:#777}
.toplink{
    display:inline-block;
    margin-top:10px;
    text-decoration:none;
    color:#222;
    font-weight:bold
}
.notice{
    margin-top:12px;
    margin-bottom:12px;
    padding:10px;
    background:#fff8e1;
    border:1px solid #f0d98a;
    border-radius:10px;
    font-size:14px;
    color:#6b5a00;
    text-align:center
}
hr{
    margin:18px 0;
    border:none;
    border-top:1px solid #eee
}
.terms{
    font-size:14px;
    color:#444;
    background:#fafafa;
    padding:12px;
    border-radius:10px;
    margin-bottom:12px;
    text-align:left
}
.checkline{
    display:flex;
    align-items:flex-start;
    gap:10px;
    margin-bottom:12px
}
.checkline input{
    width:auto;
    margin:3px 0 0 0
}
.checkline label{
    text-align:left;
    font-size:14px;
    color:#333
}
</style>
</head>
<body>
<div class="card">
    <h1>☕ STREETKIOSK</h1>
    <p>Εγγραφή νέου πελάτη</p>

    {% if message %}
        <div class="notice">{{ message }}</div>
    {% endif %}

    <form method="post" action="/register">
        <input type="text" name="name" placeholder="Όνομα πελάτη" required>
        <input type="text" name="phone" placeholder="Κινητό" required>
        <input type="email" name="email" placeholder="Email (προαιρετικό)">

        <div class="terms">
            <strong>Όροι loyalty</strong><br>
            Με την εγγραφή στο πρόγραμμα loyalty αποδέχεσαι τη χρήση των στοιχείων σου
            για τη λειτουργία της κάρτας καφέ, την καταγραφή σφραγίδων και την εξυπηρέτησή σου.
        </div>

        <div class="checkline">
            <input type="checkbox" name="terms" value="1" required>
            <label>Αποδέχομαι τους όρους του προγράμματος loyalty.</label>
        </div>

        <div class="checkline">
            <input type="checkbox" name="marketing" value="1">
            <label>Επιθυμώ να λαμβάνω προσφορές και προωθητικές ενέργειες από το STREETKIOSK μέσω κινητού και/ή email.</label>
        </div>

        <button type="submit">Δημιουργία κάρτας</button>
    </form>

    <hr>

    <form method="post" action="/search">
        <input type="text" name="phone" placeholder="Αναζήτηση πελάτη με κινητό">
        <button type="submit">Αναζήτηση</button>
    </form>

    <p><a class="toplink" href="/cashier-login">Είσοδος Ταμείου</a></p>
    <p><a class="toplink" href="/admin">Admin / Πωλήσεις</a></p>

    <div class="list">
        <strong>Πελάτες:</strong>
        {% if customers %}
            {% for customer in customers %}
                <div class="customer">
                    <a href="/customer/{{ customer['id'] }}">{{ customer["name"] }}</a><br>
                    <span class="small">{{ customer["phone"] }} | {{ customer["stamps"] }}/{{ target }} σφραγίδες</span>
                </div>
            {% endfor %}
        {% else %}
            <div class="customer">Δεν υπάρχουν πελάτες ακόμα.</div>
        {% endif %}
    </div>
</div>
</body>
</html>
"""

CUSTOMER_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Κάρτα Πελάτη</title>
<style>
body{
    font-family:Arial,sans-serif;
    background:#f4f4f4;
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:100vh;
    margin:0;
    padding:20px
}
.card{
    background:white;
    padding:30px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15);
    width:360px;
    text-align:center
}
.title{font-size:26px;font-weight:bold;margin-bottom:8px}
.name{color:#555;margin-bottom:6px;font-weight:bold}
.phone{color:#777;margin-bottom:16px;font-size:14px}
.stamps{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:15px;
    margin-top:20px;
    justify-items:center
}
.stamp{
    width:70px;
    height:70px;
    border-radius:50%;
    border:3px solid #333;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:22px;
    background:white
}
.filled{background:#222;color:white}
.reward{background:gold;border-color:#caa400}
.info{margin-top:18px;font-weight:bold}
.qrbox{margin-top:18px}
.btn2{
    display:inline-block;
    margin-top:10px;
    padding:10px 14px;
    background:#555;
    color:white;
    text-decoration:none;
    border-radius:10px
}
.tip{
    font-size:13px;
    color:#666;
    margin-top:12px
}
.history{
    margin-top:20px;
    text-align:left;
    background:#fafafa;
    padding:12px;
    border-radius:12px
}
.history h3{margin-top:0;font-size:16px}
.history-item{
    font-size:14px;
    padding:6px 0;
    border-bottom:1px solid #eee
}
.history-item:last-child{border-bottom:none}
</style>
</head>
<body>
<div class="card">
    <div class="title">☕ STREETKIOSK</div>
    <div class="name">{{ customer["name"] }}</div>
    <div class="phone">{{ customer["phone"] }}</div>

    <div class="stamps">
        <div class="stamp {% if stamps >= 1 %}filled{% endif %}">{% if stamps >= 1 %}✔{% else %}1{% endif %}</div>
        <div class="stamp {% if stamps >= 2 %}filled{% endif %}">{% if stamps >= 2 %}✔{% else %}2{% endif %}</div>
        <div class="stamp {% if stamps >= 3 %}filled{% endif %}">{% if stamps >= 3 %}✔{% else %}3{% endif %}</div>
        <div class="stamp {% if stamps >= 4 %}filled{% endif %}">{% if stamps >= 4 %}✔{% else %}4{% endif %}</div>
        <div class="stamp {% if stamps >= 5 %}filled{% endif %}">{% if stamps >= 5 %}✔{% else %}5{% endif %}</div>
        <div class="stamp reward">🎁</div>
    </div>

    <div class="info">
        {% if stamps >= target %}
            Έχεις δωρεάν καφέ! 🎉
        {% else %}
            Έχεις {{ stamps }}/{{ target }} σφραγίδες
        {% endif %}
    </div>

    <div class="qrbox">
        <p>Το QR του πελάτη</p>
        <img src="/qr/{{ customer_id }}" width="180">
    </div>

    <p class="tip">Αποθήκευσε αυτή την κάρτα στην αρχική οθόνη του κινητού σου.</p>

    <a class="btn2" href="/customer/{{ customer_id }}">Ανανέωση κάρτας</a>

    <div class="history">
        <h3>Ιστορικό</h3>
        {% if history %}
            {% for item in history %}
                <div class="history-item">{{ item["action"] }} | {{ item["created_at"] }}</div>
            {% endfor %}
        {% else %}
            <div class="history-item">Δεν υπάρχει ιστορικό ακόμα.</div>
        {% endif %}
    </div>
</div>
</body>
</html>
"""

PIN_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ταμείο Login</title>
<style>
body{
    font-family:Arial,sans-serif;
    background:#f4f4f4;
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:100vh;
    margin:0;
    padding:20px
}
.box{
    background:white;
    width:340px;
    padding:30px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15);
    text-align:center
}
input{
    width:100%;
    box-sizing:border-box;
    padding:12px;
    margin-top:12px;
    border:1px solid #ccc;
    border-radius:10px;
    font-size:18px;
    text-align:center
}
button{
    width:100%;
    padding:14px;
    margin-top:12px;
    border:none;
    border-radius:10px;
    background:#222;
    color:white;
    font-size:17px;
    cursor:pointer
}
.error{color:#b00020;margin-top:10px}
</style>
</head>
<body>
<div class="box">
    <h2>Κωδικός Ταμείου</h2>
    <p>Βάλε τον admin PIN μία φορά για να ανοίξει το ταμείο</p>
    <form method="post">
        <input type="password" name="pin" placeholder="PIN" required>
        <button type="submit">Είσοδος</button>
    </form>
    {% if error %}
        <div class="error">{{ error }}</div>
    {% endif %}
</div>
</body>
</html>
"""

ADMIN_LOGIN_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<title>Admin Login</title>
<style>
body{
    font-family:Arial,sans-serif;
    background:#f4f4f4;
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:100vh;
    margin:0;
    padding:20px
}
.box{
    background:white;
    width:360px;
    padding:30px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15);
    text-align:center
}
input{
    width:100%;
    box-sizing:border-box;
    padding:12px;
    margin-top:12px;
    border:1px solid #ccc;
    border-radius:10px;
    font-size:18px;
    text-align:center
}
button{
    width:100%;
    padding:14px;
    margin-top:12px;
    border:none;
    border-radius:10px;
    background:#222;
    color:white;
    font-size:17px;
    cursor:pointer
}
.error{color:#b00020;margin-top:10px}
</style>
</head>
<body>
<div class="box">
    <h2>Admin Login</h2>
    <p>Βάλε τον admin κωδικό για να δεις τη λίστα πελατών</p>
    <form method="post">
        <input type="password" name="password" placeholder="Admin password" required>
        <button type="submit">Είσοδος</button>
    </form>
    {% if error %}
        <div class="error">{{ error }}</div>
    {% endif %}
</div>
</body>
</html>
"""

DELETE_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<title>Διαγραφή Πελάτη</title>
<style>
body{
    font-family:Arial,sans-serif;
    background:#f4f4f4;
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:100vh;
    margin:0;
    padding:20px
}
.box{
    background:white;
    width:360px;
    padding:30px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15);
    text-align:center
}
input{
    width:100%;
    box-sizing:border-box;
    padding:12px;
    margin-top:12px;
    border:1px solid #ccc;
    border-radius:10px;
    font-size:18px;
    text-align:center
}
button{
    width:100%;
    padding:14px;
    margin-top:12px;
    border:none;
    border-radius:10px;
    background:#b00020;
    color:white;
    font-size:17px;
    cursor:pointer
}
.error{color:#b00020;margin-top:10px}
.back{
    display:inline-block;
    margin-top:12px;
    text-decoration:none;
    color:#222
}
</style>
</head>
<body>
<div class="box">
    <h2>Διαγραφή Πελάτη</h2>
    <p>Για διαγραφή βάλε τον κωδικό ασφαλείας.</p>
    <form method="post">
        <input type="password" name="delete_password" placeholder="Κωδικός διαγραφής" required>
        <button type="submit">Οριστική Διαγραφή</button>
    </form>
    {% if error %}
        <div class="error">{{ error }}</div>
    {% endif %}
    <a class="back" href="/customer/{{ customer_id }}">Επιστροφή</a>
</div>
</body>
</html>
"""

CASHIER_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ταμείο</title>
<style>
body{
    font-family:Arial,sans-serif;
    background:#f4f4f4;
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:100vh;
    margin:0;
    padding:20px
}
.panel{
    background:white;
    padding:30px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15);
    width:360px;
    text-align:center
}
.title{font-size:26px;font-weight:bold}
.name{margin-top:8px;color:#555;font-weight:bold}
.info{margin:16px 0;font-weight:bold}
.row{display:flex;gap:10px;margin-top:14px}
.row form{flex:1;margin:0}
.btn{
    width:100%;
    border:none;
    border-radius:12px;
    padding:14px 10px;
    font-size:18px;
    cursor:pointer
}
.dark{background:#222;color:white}
.gold{background:gold;color:#222}
.red{background:#b00020;color:white}
.back{
    display:inline-block;
    margin-top:18px;
    color:#222;
    text-decoration:none
}
.logout{
    display:inline-block;
    margin-top:10px;
    color:#b00020;
    text-decoration:none;
    font-weight:bold
}
</style>
</head>
<body>
<div class="panel">
    <div class="title">☕ STREETKIOSK</div>
    <div class="name">{{ customer["name"] }}</div>
    <div class="info">{{ stamps }}/{{ target }} σφραγίδες</div>

    <div class="row">
        <form method="post" action="/add/{{ customer_id }}/1">
            <button class="btn dark" type="submit">+1</button>
        </form>
        <form method="post" action="/add/{{ customer_id }}/2">
            <button class="btn dark" type="submit">+2</button>
        </form>
        <form method="post" action="/add/{{ customer_id }}/3">
            <button class="btn dark" type="submit">+3</button>
        </form>
    </div>

    <div class="row">
        <form method="post" action="/redeem/{{ customer_id }}">
            <button class="btn gold" type="submit">Εξαργύρωση Δώρου</button>
        </form>
    </div>

    <div class="row">
        <form method="get" action="/delete/{{ customer_id }}">
            <button class="btn red" type="submit">Διαγραφή Πελάτη</button>
        </form>
    </div>

    <a class="back" href="/customer/{{ customer_id }}">Επιστροφή στην κάρτα</a><br>
    <a class="logout" href="/cashier-logout">Logout Ταμείου</a>
</div>
</body>
</html>
"""

RESULT_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="1.5;url=/customer/{{ customer_id }}">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Αποτέλεσμα</title>
<style>
body{
    font-family:Arial,sans-serif;
    background:#f4f4f4;
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:100vh;
    margin:0
}
.box{
    background:white;
    padding:30px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15);
    width:320px;
    text-align:center
}
</style>
</head>
<body>
<div class="box">
    <h2>{{ message }}</h2>
    <p>{{ stamps }}/{{ target }} σφραγίδες</p>
</div>
</body>
</html>
"""

SCANNER_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scanner</title>
<script src="https://unpkg.com/html5-qrcode"></script>
<style>
body{
    font-family:Arial,sans-serif;
    background:#f4f4f4;
    margin:0;
    padding:20px;
    text-align:center
}
.box{
    max-width:500px;
    margin:0 auto;
    background:white;
    padding:20px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15)
}
#reader{width:100%;margin-top:20px}
.btn{
    display:inline-block;
    margin-top:14px;
    padding:10px 14px;
    background:#222;
    color:white;
    text-decoration:none;
    border-radius:10px
}
.logout{
    display:inline-block;
    margin-top:10px;
    color:#b00020;
    text-decoration:none;
    font-weight:bold
}
</style>
</head>
<body>
<div class="box">
    <h2>📷 Scanner Πελάτη</h2>
    <p>Σκάναρε το QR του πελάτη για να ανοίξει το ταμείο του</p>
    <div id="reader"></div>
    <a class="btn" href="/">Πίσω</a><br>
    <a class="logout" href="/cashier-logout">Logout Ταμείου</a>
</div>

<script>
function onScanSuccess(decodedText) {
    if (decodedText.includes("/customer/")) {
        const parts = decodedText.split("/customer/");
        const customerId = parts[1].split(/[?#]/)[0];
        window.location.href = "/cashier/" + customerId;
    }
}

const html5QrcodeScanner = new Html5QrcodeScanner(
    "reader",
    { fps: 10, qrbox: 220 },
    false
);

html5QrcodeScanner.render(onScanSuccess);
</script>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<title>Admin</title>
<style>
body{font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:20px}
.wrap{max-width:900px;margin:0 auto}
.card{
    background:white;
    padding:20px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15);
    margin-bottom:20px
}
table{width:100%;border-collapse:collapse}
th,td{
    padding:10px;
    border-bottom:1px solid #eee;
    text-align:left;
    font-size:14px
}
.logout{
    display:inline-block;
    margin-top:10px;
    color:#b00020;
    text-decoration:none;
    font-weight:bold
}
</style>
</head>
<body>
<div class="wrap">
    <div class="card">
        <h2>Σύνοψη</h2>
        <p>Πελάτες: {{ total_customers }}</p>
        <p>Καφέδες που περάστηκαν: {{ total_added }}</p>
        <p>Εξαργυρώσεις: {{ total_redeems }}</p>
        <a class="logout" href="/admin-logout">Logout Admin</a>
    </div>

    <div class="card">
        <h2>Πελάτες</h2>
        <table>
            <tr>
                <th>ID</th>
                <th>Όνομα</th>
                <th>Κινητό</th>
                <th>Email</th>
                <th>Σφραγίδες</th>
                <th>Marketing</th>
            </tr>
            {% for c in customers %}
            <tr>
                <td>{{ c["id"] }}</td>
                <td>{{ c["name"] }}</td>
                <td>{{ c["phone"] }}</td>
                <td>{{ c["email"] or "" }}</td>
                <td>{{ c["stamps"] }}</td>
                <td>{{ "Ναι" if c["marketing_consent"] else "Όχι" }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</div>
</body>
</html>
"""


@app.route("/")
def home():
    message = request.args.get("message", "")
    conn = get_db()
    customers = conn.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()
    conn.close()
    return render_template_string(
        REGISTER_HTML,
        customers=customers,
        target=TARGET,
        message=message
    )


@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip().lower()

    if email == "":
        email = None

    terms = 1 if request.form.get("terms") == "1" else 0
    marketing = 1 if request.form.get("marketing") == "1" else 0

    if not name or not phone or not terms:
        return redirect(url_for("home", message="Συμπλήρωσε όνομα, κινητό και αποδοχή όρων"))

    conn = get_db()

    if email:
        existing = conn.execute(
            "SELECT id FROM customers WHERE phone = ? OR email = ?",
            (phone, email)
        ).fetchone()
    else:
        existing = conn.execute(
            "SELECT id FROM customers WHERE phone = ?",
            (phone,)
        ).fetchone()

    if existing:
        conn.close()
        return redirect(url_for("customer_card", customer_id=existing["id"]))

    accepted_at = now_str()
    marketing_at = accepted_at if marketing else None

    cur = conn.execute("""
        INSERT INTO customers
        (name, phone, email, stamps, terms_accepted, marketing_consent,
         terms_accepted_at, marketing_consent_at, created_at)
        VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?)
    """, (
        name,
        phone,
        email,
        terms,
        marketing,
        accepted_at,
        marketing_at,
        accepted_at
    ))

    customer_id = cur.lastrowid

    conn.execute(
        "INSERT INTO history (customer_id, action, created_at) VALUES (?, ?, ?)",
        (customer_id, "Εγγραφή πελάτη", accepted_at)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("customer_card", customer_id=customer_id))


@app.route("/search", methods=["POST"])
def search():
    phone = request.form.get("phone", "").strip()
    if not phone:
        return redirect(url_for("home"))

    conn = get_db()
    customer = conn.execute(
        "SELECT id FROM customers WHERE phone = ?",
        (phone,)
    ).fetchone()
    conn.close()

    if customer:
        return redirect(url_for("customer_card", customer_id=customer["id"]))

    return redirect(url_for("home", message="Δεν βρέθηκε πελάτης"))


@app.route("/customer/<int:customer_id>")
def customer_card(customer_id):
    conn = get_db()
    customer = conn.execute(
        "SELECT * FROM customers WHERE id = ?",
        (customer_id,)
    ).fetchone()

    history = conn.execute(
        "SELECT * FROM history WHERE customer_id = ? ORDER BY id DESC",
        (customer_id,)
    ).fetchall()

    conn.close()

    if not customer:
        return "Ο πελάτης δεν βρέθηκε", 404

    return render_template_string(
        CUSTOMER_HTML,
        customer=customer,
        customer_id=customer_id,
        stamps=customer["stamps"],
        target=TARGET,
        history=history
    )


@app.route("/cashier-login", methods=["GET", "POST"])
def cashier_login():
    if cashier_logged_in():
        return redirect(url_for("scanner"))

    if request.method == "POST":
        pin = request.form.get("pin", "")
        if pin == ADMIN_PIN:
            session["cashier_auth"] = True
            return redirect(url_for("scanner"))
        return render_template_string(PIN_HTML, error="Λάθος PIN")

    return render_template_string(PIN_HTML, error="")


@app.route("/cashier-logout")
def cashier_logout():
    session.pop("cashier_auth", None)
    return redirect(url_for("cashier_login"))


@app.route("/cashier/<int:customer_id>")
def cashier(customer_id):
    if not cashier_logged_in():
        return redirect(url_for("cashier_login"))

    conn = get_db()
    customer = conn.execute(
        "SELECT * FROM customers WHERE id = ?",
        (customer_id,)
    ).fetchone()
    conn.close()

    if not customer:
        return "Ο πελάτης δεν βρέθηκε", 404

    return render_template_string(
        CASHIER_HTML,
        customer=customer,
        customer_id=customer_id,
        stamps=customer["stamps"],
        target=TARGET
    )


@app.route("/add/<int:customer_id>/<int:amount>", methods=["POST"])
def add_stamps(customer_id, amount):
    if not cashier_logged_in():
        return redirect(url_for("cashier_login"))

    if amount not in [1, 2, 3]:
        return "Μη έγκυρος αριθμός καφέδων", 400

    conn = get_db()
    customer = conn.execute(
        "SELECT * FROM customers WHERE id = ?",
        (customer_id,)
    ).fetchone()

    if not customer:
        conn.close()
        return "Ο πελάτης δεν βρέθηκε", 404

    new_stamps = customer["stamps"] + amount
    if new_stamps > TARGET:
        new_stamps = TARGET

    conn.execute(
        "UPDATE customers SET stamps = ? WHERE id = ?",
        (new_stamps, customer_id)
    )

    action_text = f"+{amount} καφές" if amount == 1 else f"+{amount} καφέδες"

    conn.execute(
        "INSERT INTO history (customer_id, action, created_at) VALUES (?, ?, ?)",
        (customer_id, action_text, now_str())
    )

    conn.commit()
    conn.close()

    message = "Έφτασε δώρο 🎁" if new_stamps >= TARGET else f"Προστέθηκαν {amount} καφέδες ☕"

    return render_template_string(
        RESULT_HTML,
        message=message,
        stamps=new_stamps,
        target=TARGET,
        customer_id=customer_id
    )


@app.route("/redeem/<int:customer_id>", methods=["POST"])
def redeem(customer_id):
    if not cashier_logged_in():
        return redirect(url_for("cashier_login"))

    conn = get_db()
    customer = conn.execute(
        "SELECT * FROM customers WHERE id = ?",
        (customer_id,)
    ).fetchone()

    if not customer:
        conn.close()
        return "Ο πελάτης δεν βρέθηκε", 404

    if customer["stamps"] < TARGET:
        conn.close()
        return render_template_string(
            RESULT_HTML,
            message="Δεν υπάρχει ακόμα δώρο",
            stamps=customer["stamps"],
            target=TARGET,
            customer_id=customer_id
        )

    conn.execute(
        "UPDATE customers SET stamps = 0 WHERE id = ?",
        (customer_id,)
    )

    conn.execute(
        "INSERT INTO history (customer_id, action, created_at) VALUES (?, ?, ?)",
        (customer_id, "Εξαργύρωση δώρου", now_str())
    )

    conn.commit()
    conn.close()

    return render_template_string(
        RESULT_HTML,
        message="Το δώρο εξαργυρώθηκε ✅",
        stamps=0,
        target=TARGET,
        customer_id=customer_id
    )


@app.route("/delete/<int:customer_id>", methods=["GET", "POST"])
def delete_customer(customer_id):
    if not cashier_logged_in():
        return redirect(url_for("cashier_login"))

    if request.method == "GET":
        return render_template_string(DELETE_HTML, customer_id=customer_id, error="")

    delete_password = request.form.get("delete_password", "")
    if delete_password != DELETE_PASSWORD:
        return render_template_string(
            DELETE_HTML,
            customer_id=customer_id,
            error="Λάθος κωδικός διαγραφής"
        )

    conn = get_db()
    conn.execute("DELETE FROM history WHERE customer_id = ?", (customer_id,))
    conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("home", message="Ο πελάτης διαγράφηκε"))


@app.route("/scanner")
def scanner():
    if not cashier_logged_in():
        return redirect(url_for("cashier_login"))
    return render_template_string(SCANNER_HTML)


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if admin_logged_in():
        return redirect(url_for("admin"))

    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["admin_auth"] = True
            return redirect(url_for("admin"))
        return render_template_string(ADMIN_LOGIN_HTML, error="Λάθος admin password")

    return render_template_string(ADMIN_LOGIN_HTML, error="")


@app.route("/admin-logout")
def admin_logout():
    session.pop("admin_auth", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
def admin():
    if not admin_logged_in():
        return redirect(url_for("admin_login"))

    conn = get_db()
    customers = conn.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()
    rows = conn.execute("SELECT action FROM history").fetchall()
    conn.close()

    total_added = 0
    total_redeems = 0

    for r in rows:
        action = r["action"]

        if action.startswith("+"):
            try:
                total_added += int(action[1])
            except Exception:
                pass

        if action == "Εξαργύρωση δώρου":
            total_redeems += 1

    return render_template_string(
        ADMIN_HTML,
        customers=customers,
        total_customers=len(customers),
        total_added=total_added,
        total_redeems=total_redeems
    )


@app.route("/qr/<int:customer_id>")
def qr(customer_id):
    conn = get_db()
    customer = conn.execute(
        "SELECT id FROM customers WHERE id = ?",
        (customer_id,)
    ).fetchone()
    conn.close()

    if not customer:
        return "Ο πελάτης δεν βρέθηκε", 404

    payload = url_for("customer_card", customer_id=customer_id, _external=True)

    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return send_file(buf, mimetype="image/png")


if __name__ == "__main__":
    app.run(debug=True)
