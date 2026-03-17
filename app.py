
from flask import Flask, render_template_string, send_file, redirect, url_for, request, session
import io
import os
import qrcode
import secrets
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "streetkiosk-secret-key-2026")

DB_NAME = "streetkiosk.db"
TARGET = 5
GREECE_TZ = ZoneInfo("Europe/Athens")

CASHIER_PIN = os.environ.get("ADMIN_PIN", "2580")
DELETE_PASSWORD = os.environ.get("DELETE_PASSWORD", "STRATOS1976!!!")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "STRATOSADMIN2026")


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def now_str():
    return datetime.now(GREECE_TZ).strftime("%d-%m-%Y %H:%M")


def cashier_logged_in():
    return session.get("cashier_auth") is True


def admin_logged_in():
    return session.get("admin_auth") is True


def generate_token():
    return secrets.token_urlsafe(12)


def ensure_unique_token(conn):
    token = generate_token()
    while conn.execute("SELECT id FROM customers WHERE card_token = ?", (token,)).fetchone():
        token = generate_token()
    return token


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_token TEXT UNIQUE,
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

    columns = [row["name"] for row in conn.execute("PRAGMA table_info(customers)").fetchall()]
    if "card_token" not in columns:
        conn.execute("ALTER TABLE customers ADD COLUMN card_token TEXT")

    rows = conn.execute("""
        SELECT id FROM customers
        WHERE card_token IS NULL OR card_token = ''
    """).fetchall()

    for row in rows:
        token = ensure_unique_token(conn)
        conn.execute(
            "UPDATE customers SET card_token = ? WHERE id = ?",
            (token, row["id"])
        )

    conn.commit()
    conn.close()


init_db()


def get_customer_by_token(token):
    conn = get_db()
    customer = conn.execute(
        "SELECT * FROM customers WHERE card_token = ?",
        (token,)
    ).fetchone()
    conn.close()
    return customer


def get_customer_stats(conn, customer_id):
    rows = conn.execute(
        "SELECT action FROM history WHERE customer_id = ? ORDER BY id ASC",
        (customer_id,)
    ).fetchall()

    total_coffees = 0
    total_gifts = 0

    for row in rows:
        action = row["action"]

        if action.startswith("+"):
            try:
                total_coffees += int(action[1])
            except Exception:
                pass

        if action == "Αυτόματο δώρο":
            total_gifts += 1

    return total_coffees, total_gifts


def get_current_cycle_history(conn, customer_id):
    last_reward = conn.execute("""
        SELECT id FROM history
        WHERE customer_id = ? AND action = 'Αυτόματο δώρο'
        ORDER BY id DESC
        LIMIT 1
    """, (customer_id,)).fetchone()

    if last_reward:
        return conn.execute("""
            SELECT * FROM history
            WHERE customer_id = ?
              AND id > ?
              AND action != 'Αυτόματο δώρο'
              AND action != 'Εγγραφή πελάτη'
            ORDER BY id DESC
        """, (customer_id, last_reward["id"])).fetchall()

    return conn.execute("""
        SELECT * FROM history
        WHERE customer_id = ?
          AND action != 'Εγγραφή πελάτη'
        ORDER BY id DESC
    """, (customer_id,)).fetchall()


HOME_HTML = """
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
    margin:0;
    padding:20px;
}
.wrap{
    max-width:980px;
    margin:0 auto;
}
.grid{
    display:grid;
    grid-template-columns:1.2fr 1fr;
    gap:20px;
}
.card{
    background:white;
    padding:24px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.12);
}
h1,h2,h3{margin-top:0}
p{color:#666}
input{
    width:100%;
    box-sizing:border-box;
    padding:12px;
    margin-bottom:12px;
    border:1px solid #ccc;
    border-radius:10px;
    font-size:16px;
}
button{
    width:100%;
    padding:14px;
    border:none;
    border-radius:10px;
    background:#222;
    color:white;
    font-size:16px;
    cursor:pointer;
}
.secondary{
    background:#666;
}
.notice{
    margin-bottom:12px;
    padding:10px;
    background:#fff8e1;
    border:1px solid #f0d98a;
    border-radius:10px;
    font-size:14px;
    color:#6b5a00;
    text-align:center;
}
.toplinks a{
    display:inline-block;
    margin-right:14px;
    margin-bottom:10px;
    text-decoration:none;
    color:#222;
    font-weight:bold;
}
.list{
    margin-top:16px;
    max-height:380px;
    overflow:auto;
}
.customer{
    padding:10px;
    background:#fafafa;
    border-radius:10px;
    margin-bottom:8px;
}
.customer a{
    text-decoration:none;
    color:#222;
    font-weight:bold;
}
.small{
    font-size:13px;
    color:#777;
}
.terms{
    font-size:14px;
    color:#444;
    background:#fafafa;
    padding:12px;
    border-radius:10px;
    margin-bottom:12px;
    text-align:left;
}
.checkline{
    display:flex;
    align-items:flex-start;
    gap:10px;
    margin-bottom:12px;
}
.checkline input{
    width:auto;
    margin:3px 0 0 0;
}
.checkline label{
    text-align:left;
    font-size:14px;
    color:#333;
}
.qrbox{
    text-align:center;
}
.qrbox img{
    border-radius:12px;
    background:#fff;
    padding:8px;
}
.tip{
    font-size:13px;
    color:#666;
}
@media (max-width: 860px){
    .grid{
        grid-template-columns:1fr;
    }
}
</style>
</head>
<body>
<div class="wrap">
    <div class="grid">
        <div class="card">
            <h1>☕ STREETKIOSK</h1>
            <p>Ταμείο / Εγγραφή πελάτη</p>

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
                <button class="secondary" type="submit">Αναζήτηση</button>
            </form>

            <div class="toplinks">
                <a href="/cashier-login">Είσοδος ταμείου</a>
                <a href="/admin">Admin / Στατιστικά</a>
            </div>

            <div class="list">
                <h3>Πελάτες</h3>
                {% if customers %}
                    {% for customer in customers %}
                        <div class="customer">
                            <a href="/card/{{ customer['card_token'] }}">{{ customer["name"] }}</a><br>
                            <span class="small">{{ customer["phone"] }} | {{ customer["stamps"] }}/{{ target }} σφραγίδες</span>
                        </div>
                    {% endfor %}
                {% else %}
                    <div class="customer">Δεν υπάρχουν πελάτες ακόμα.</div>
                {% endif %}
            </div>
        </div>

        <div class="card qrbox">
            <h2>QR εγγραφής</h2>
            <p>Ο νέος πελάτης το σκανάρει για να ανοίξει η σελίδα υποδοχής στο κινητό του.</p>
            <img src="/join-qr" width="220">
            <p class="tip">
                Στη συνέχεια εσύ κάνεις την εγγραφή από τη φόρμα αριστερά.<br>
                Μόλις ολοκληρωθεί, θα εμφανιστεί το προσωπικό του QR για σκανάρισμα.
            </p>
        </div>
    </div>
</div>
</body>
</html>
"""

JOIN_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>STREETKIOSK Loyalty</title>
<style>
body{
    font-family:Arial,sans-serif;
    background:#f4f4f4;
    margin:0;
    padding:20px;
}
.card{
    max-width:480px;
    margin:0 auto;
    background:white;
    padding:28px;
    border-radius:18px;
    box-shadow:0 5px 20px rgba(0,0,0,0.12);
    text-align:center;
}
h1{margin-top:0}
p{color:#666;line-height:1.5}
.note{
    margin-top:18px;
    padding:12px;
    background:#fafafa;
    border-radius:12px;
    color:#444;
}
</style>
</head>
<body>
<div class="card">
    <h1>☕ Καλώς ήρθες</h1>
    <p>
        Το STREETKIOSK θα σου φτιάξει τώρα την προσωπική loyalty κάρτα σου.
    </p>
    <div class="note">
        Δώσε το κινητό σου στο ταμείο για να ολοκληρωθεί η εγγραφή σου.<br>
        Μόλις ολοκληρωθεί, σκάναρε το προσωπικό σου QR από την οθόνη του ταμείου.
    </div>
</div>
</body>
</html>
"""

DELIVER_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Νέα κάρτα πελάτη</title>
<style>
body{
    font-family:Arial,sans-serif;
    background:#f4f4f4;
    margin:0;
    padding:20px;
}
.card{
    max-width:560px;
    margin:0 auto;
    background:white;
    padding:28px;
    border-radius:18px;
    box-shadow:0 5px 20px rgba(0,0,0,0.12);
    text-align:center;
}
h1{margin-top:0}
p{color:#666}
img{
    background:white;
    padding:8px;
    border-radius:12px;
}
.btn{
    display:inline-block;
    margin-top:14px;
    padding:12px 16px;
    background:#222;
    color:white;
    text-decoration:none;
    border-radius:10px;
}
.small{
    font-size:13px;
    color:#666;
    margin-top:12px;
}
</style>
</head>
<body>
<div class="card">
    <h1>✅ Η κάρτα δημιουργήθηκε</h1>
    <p><strong>{{ customer["name"] }}</strong></p>
    <p>Ο πελάτης σκανάρει τώρα το προσωπικό του QR για να ανοίξει τη δική του μυστική κάρτα.</p>

    <img src="/qr/{{ customer['card_token'] }}" width="240">

    <div>
        <a class="btn" href="/card/{{ customer['card_token'] }}" target="_blank">Άνοιγμα προσωπικής κάρτας</a>
    </div>

    <p class="small">
        Μετά το σκανάρισμα, ο πελάτης μπορεί να πατήσει
        <strong>«Αποθήκευση στην αρχική οθόνη»</strong>.
    </p>

    <div>
        <a class="btn" href="/">Επιστροφή στο ταμείο</a>
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
<meta http-equiv="refresh" content="20">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Η κάρτα μου</title>
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="STREETKIOSK">
<style>
body{
    font-family:Arial,sans-serif;
    background:#f4f4f4;
    margin:0;
    padding:20px;
}
.card{
    max-width:420px;
    margin:0 auto;
    background:white;
    padding:28px;
    border-radius:18px;
    box-shadow:0 5px 20px rgba(0,0,0,0.12);
    text-align:center;
}
.title{font-size:28px;font-weight:bold;margin-bottom:8px}
.name{font-size:20px;font-weight:bold;color:#444}
.phone{font-size:14px;color:#777;margin-top:6px}
.stats{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:10px;
    margin-top:18px;
}
.stat{
    background:#fafafa;
    border-radius:12px;
    padding:12px;
}
.stat strong{
    display:block;
    font-size:20px;
    color:#222;
}
.stamps{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:14px;
    margin-top:20px;
    justify-items:center;
}
.stamp{
    width:72px;
    height:72px;
    border-radius:50%;
    border:3px solid #333;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:22px;
    background:white;
}
.filled{background:#222;color:white}
.reward{background:gold;border-color:#caa400}
.info{margin-top:18px;font-weight:bold}
.qrbox{margin-top:18px}
.btn{
    display:inline-block;
    margin-top:10px;
    padding:12px 16px;
    background:#222;
    color:white;
    text-decoration:none;
    border-radius:10px;
    border:none;
    cursor:pointer;
}
.btn.secondary{
    background:#666;
}
.tip{
    font-size:13px;
    color:#666;
    margin-top:12px;
}
.history{
    margin-top:22px;
    text-align:left;
    background:#fafafa;
    padding:14px;
    border-radius:12px;
}
.history h3{
    margin-top:0;
    font-size:16px;
}
.history-item{
    font-size:14px;
    padding:6px 0;
    border-bottom:1px solid #eee;
}
.history-item:last-child{
    border-bottom:none;
}
.install-box{
    margin-top:16px;
    background:#f7fbff;
    border:1px solid #d6ebff;
    color:#244b73;
    border-radius:12px;
    padding:12px;
    font-size:14px;
}
</style>
</head>
<body>
<div class="card">
    <div class="title">☕ STREETKIOSK</div>
    <div class="name">{{ customer["name"] }}</div>
    <div class="phone">{{ customer["phone"] }}</div>

    <div class="stats">
        <div class="stat">
            <span>Τρέχων κύκλος</span>
            <strong>{{ stamps }}/{{ target }}</strong>
        </div>
        <div class="stat">
            <span>Συνολικά δώρα</span>
            <strong>{{ total_gifts }}</strong>
        </div>
        <div class="stat">
            <span>Συνολικοί καφέδες</span>
            <strong>{{ total_coffees }}</strong>
        </div>
        <div class="stat">
            <span>Εγγραφή</span>
            <strong style="font-size:14px">{{ customer["created_at"] }}</strong>
        </div>
    </div>

    <div class="stamps">
        <div class="stamp {% if stamps >= 1 %}filled{% endif %}">{% if stamps >= 1 %}✔{% else %}1{% endif %}</div>
        <div class="stamp {% if stamps >= 2 %}filled{% endif %}">{% if stamps >= 2 %}✔{% else %}2{% endif %}</div>
        <div class="stamp {% if stamps >= 3 %}filled{% endif %}">{% if stamps >= 3 %}✔{% else %}3{% endif %}</div>
        <div class="stamp {% if stamps >= 4 %}filled{% endif %}">{% if stamps >= 4 %}✔{% else %}4{% endif %}</div>
        <div class="stamp {% if stamps >= 5 %}filled{% endif %}">{% if stamps >= 5 %}✔{% else %}5{% endif %}</div>
        <div class="stamp reward">🎁</div>
    </div>

    <div class="info">
        Έχεις {{ stamps }}/{{ target }} σφραγίδες
    </div>

    <div class="qrbox">
        <p>Το προσωπικό μου QR</p>
        <img src="/qr/{{ customer['card_token'] }}" width="180">
    </div>
html <button class="btn" id="installButton">Αποθήκευση στην αρχική οθόνη</button> <div class="install-box" id="installInfo"> Πάτησε το κουμπί για να αποθηκεύσεις την κάρτα σου στην αρχική οθόνη. </div> ``` --- ### 2) Μετά, στο κάτω μέρος του `CUSTOMER_HTML`, βρες όλο το `<script>...</script>` και **αντικατάστησέ το όλο** με αυτό: ```html <script> let deferredPrompt = null; const installButton = document.getElementById("installButton"); const installInfo = document.getElementById("installInfo"); window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); deferredPrompt = e; }); installButton.addEventListener("click", async () => { const isIos = /iphone|ipad|ipod/i.test(window.navigator.userAgent); const isInStandaloneMode = ("standalone" in window.navigator) && window.navigator.standalone; if (isIos && !isInStandaloneMode) { alert("Σε iPhone πάτησε Κοινοποίηση και μετά «Προσθήκη στην αρχική οθόνη»."); return; } if (deferredPrompt) { deferredPrompt.prompt(); await deferredPrompt.userChoice; deferredPrompt = null; installInfo.innerText =

    <a class="btn secondary" href="/card/{{ customer['card_token'] }}">Ανανέωση κάρτας</a>

    <div class="history">
        <h3>Τρέχων κύκλος</h3>
        {% if history %}
            {% for item in history %}
                <div class="history-item">{{ item["action"] }} | {{ item["created_at"] }}</div>
            {% endfor %}
        {% else %}
            <div class="history-item">Δεν υπάρχει ιστορικό ακόμα.</div>
        {% endif %}
    </div>
</div>

<script>
let deferredPrompt = null;
const installButton = document.getElementById("installButton");
const iosButton = document.getElementById("iosButton");
const installInfo = document.getElementById("installInfo");

window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    installButton.style.display = "inline-block";
    installInfo.innerText = "Πάτησε το κουμπί για αποθήκευση στην αρχική οθόνη.";
});

installButton.addEventListener("click", async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    deferredPrompt = null;
    installButton.style.display = "none";
});

const isIos = /iphone|ipad|ipod/i.test(window.navigator.userAgent);
const isInStandaloneMode = ("standalone" in window.navigator) && window.navigator.standalone;

if (isIos && !isInStandaloneMode) {
    iosButton.style.display = "inline-block";
    installInfo.innerText = "Σε iPhone: πάτησε το κουμπί και ακολούθησε τις οδηγίες.";
}

iosButton.addEventListener("click", () => {
    alert("Σε iPhone πάτησε Κοινοποίηση και μετά «Προσθήκη στην αρχική οθόνη».");
});
</script>
</body>
</html>
"""

PIN_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Είσοδος ταμείου</title>
<style>
body{
    font-family:Arial,sans-serif;
    background:#f4f4f4;
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:100vh;
    margin:0;
    padding:20px;
}
.box{
    background:white;
    width:340px;
    padding:30px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15);
    text-align:center;
}
input{
    width:100%;
    box-sizing:border-box;
    padding:12px;
    margin-top:12px;
    border:1px solid #ccc;
    border-radius:10px;
    font-size:18px;
    text-align:center;
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
    cursor:pointer;
}
.error{color:#b00020;margin-top:10px}
</style>
</head>
<body>
<div class="box">
    <h2>Κωδικός ταμείου</h2>
    <p>Βάλε το PIN μία φορά για να ανοίξει το ταμείο.</p>
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
    padding:20px;
}
.panel{
    background:white;
    padding:30px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15);
    width:420px;
    text-align:center;
}
.title{font-size:28px;font-weight:bold}
.name{margin-top:8px;color:#555;font-weight:bold;font-size:24px}
.phone{margin-top:4px;color:#777;font-size:14px}
.info{margin:16px 0;font-weight:bold;font-size:22px}
.row{display:flex;gap:10px;margin-top:14px}
.row form{flex:1;margin:0}
.btn{
    width:100%;
    border:none;
    border-radius:12px;
    padding:18px 10px;
    font-size:20px;
    cursor:pointer;
}
.dark{background:#222;color:white}
.red{background:#b00020;color:white}
.back{
    display:inline-block;
    margin-top:18px;
    color:#222;
    text-decoration:none;
}
.logout{
    display:inline-block;
    margin-top:10px;
    color:#b00020;
    text-decoration:none;
    font-weight:bold;
}
.note{
    margin-top:14px;
    color:#666;
    font-size:13px;
}
</style>
</head>
<body>
<div class="panel">
    <div class="title">☕ STREETKIOSK</div>
    <div class="name">{{ customer["name"] }}</div>
    <div class="phone">{{ customer["phone"] }}</div>
    <div class="info">{{ stamps }}/{{ target }} σφραγίδες</div>

    <div class="row">
        <form method="post" action="/add/{{ customer['card_token'] }}/1">
            <button class="btn dark" type="submit">+1</button>
        </form>
        <form method="post" action="/add/{{ customer['card_token'] }}/2">
            <button class="btn dark" type="submit">+2</button>
        </form>
        <form method="post" action="/add/{{ customer['card_token'] }}/3">
            <button class="btn dark" type="submit">+3</button>
        </form>
    </div>

    <div class="row">
        <form method="post" action="/add/{{ customer['card_token'] }}/4">
            <button class="btn dark" type="submit">+4</button>
        </form>
        <form method="post" action="/add/{{ customer['card_token'] }}/5">
            <button class="btn dark" type="submit">+5</button>
        </form>
    </div>

    <div class="row">
        <form method="get" action="/delete/{{ customer['card_token'] }}">
            <button class="btn red" type="submit">Διαγραφή πελάτη</button>
        </form>
    </div>

    <div class="note">Το δώρο δίνεται αυτόματα στο 5ο.</div>

    <a class="back" href="/scanner">Πίσω στο scanner</a><br>
    <a class="logout" href="/cashier-logout">Έξοδος ταμείου</a>
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
    text-align:center;
}
.box{
    max-width:640px;
    margin:0 auto;
    background:white;
    padding:24px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15);
}
#reader{
    width:100%;
    margin-top:20px;
    min-height:320px;
}
.actions{
    display:flex;
    gap:12px;
    margin-top:16px;
    justify-content:center;
    flex-wrap:wrap;
}
.btn{
    display:inline-block;
    padding:14px 18px;
    background:#222;
    color:white;
    text-decoration:none;
    border-radius:12px;
    border:none;
    font-size:18px;
    cursor:pointer;
    min-width:180px;
}
.btn.secondary{background:#666}
.btn.green{background:#0a7d32}
.logout{
    display:inline-block;
    margin-top:14px;
    color:#b00020;
    text-decoration:none;
    font-weight:bold;
}
.small{
    color:#666;
    font-size:14px;
    margin-top:10px;
}
.status{
    margin-top:14px;
    font-weight:bold;
    color:#333;
}
</style>
</head>
<body>
<div class="box">
    <h2>📷 Scanner πελάτη</h2>
    <p>Tablet flow: σκάναρε → άνοιγμα ταμείου → καταχώρηση</p>

    <div class="actions">
        <button class="btn green" onclick="startScanner()">Σκάναρε</button>
        <a class="btn secondary" href="/">Νέα εγγραφή</a>
    </div>

    <div id="reader"></div>
    <div class="status" id="status">Το scanner είναι έτοιμο.</div>
    <div class="small">Θα προσπαθήσει πρώτα να ανοίξει την πίσω κάμερα.</div>

    <a class="logout" href="/cashier-logout">Έξοδος ταμείου</a>
</div>

<script>
let html5QrCode = new Html5Qrcode("reader");
let scannerStarted = false;
let handlingScan = false;

async function startScanner() {
    if (scannerStarted) {
        document.getElementById("status").innerText = "Το scanner δουλεύει ήδη.";
        return;
    }

    document.getElementById("status").innerText = "Εκκίνηση κάμερας...";

    const config = {
        fps: 10,
        qrbox: { width: 260, height: 260 },
        aspectRatio: 1.333333
    };

    try {
        await html5QrCode.start(
            { facingMode: { exact: "environment" } },
            config,
            onScanSuccess
        );
        scannerStarted = true;
        document.getElementById("status").innerText = "Σκάναρε το QR του πελάτη.";
        return;
    } catch (e) {
    }

    try {
        const cameras = await Html5Qrcode.getCameras();
        if (!cameras || cameras.length === 0) {
            document.getElementById("status").innerText = "Δεν βρέθηκε κάμερα.";
            return;
        }

        let selectedCamera = cameras[0].id;

        for (const cam of cameras) {
            const label = (cam.label || "").toLowerCase();
            if (
                label.includes("back") ||
                label.includes("rear") ||
                label.includes("environment")
            ) {
                selectedCamera = cam.id;
                break;
            }
        }

        await html5QrCode.start(
            selectedCamera,
            config,
            onScanSuccess
        );
        scannerStarted = true;
        document.getElementById("status").innerText = "Σκάναρε το QR του πελάτη.";
    } catch (err) {
        document.getElementById("status").innerText = "Δεν άνοιξε η κάμερα.";
    }
}

async function onScanSuccess(decodedText) {
    if (handlingScan) return;
    handlingScan = true;

    document.getElementById("status").innerText = "Άνοιγμα πελάτη...";

    try {
        if (scannerStarted) {
            await html5QrCode.stop();
            scannerStarted = false;
        }
    } catch (e) {
    }

    if (decodedText.includes("/card/")) {
        const parts = decodedText.split("/card/");
        const token = parts[1].split(/[?#]/)[0];
        window.location.href = "/cashier/card/" + token;
        return;
    }

    window.location.href = decodedText;
}
</script>
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
    padding:20px;
}
.box{
    background:white;
    width:360px;
    padding:30px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15);
    text-align:center;
}
input{
    width:100%;
    box-sizing:border-box;
    padding:12px;
    margin-top:12px;
    border:1px solid #ccc;
    border-radius:10px;
    font-size:18px;
    text-align:center;
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
    cursor:pointer;
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

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<title>Admin</title>
<style>
body{font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:20px}
.wrap{max-width:980px;margin:0 auto}
.card{
    background:white;
    padding:20px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15);
    margin-bottom:20px;
}
table{width:100%;border-collapse:collapse}
th,td{
    padding:10px;
    border-bottom:1px solid #eee;
    text-align:left;
    font-size:14px;
}
a{color:#222}
.logout{
    display:inline-block;
    margin-top:10px;
    color:#b00020;
    text-decoration:none;
    font-weight:bold;
}
</style>
</head>
<body>
<div class="wrap">
    <div class="card">
        <h2>Σύνοψη</h2>
        <p>Πελάτες: {{ total_customers }}</p>
        <p>Καφέδες που περάστηκαν: {{ total_added }}</p>
        <p>Δώρα που δόθηκαν: {{ total_redeems }}</p>
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
                <th>Κάρτα</th>
            </tr>
            {% for c in customers %}
            <tr>
                <td>{{ c["id"] }}</td>
                <td>{{ c["name"] }}</td>
                <td>{{ c["phone"] }}</td>
                <td>{{ c["email"] or "" }}</td>
                <td>{{ c["stamps"] }}</td>
                <td>{{ "Ναι" if c["marketing_consent"] else "Όχι" }}</td>
                <td><a href="/card/{{ c['card_token'] }}" target="_blank">Άνοιγμα</a></td>
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
        HOME_HTML,
        customers=customers,
        target=TARGET,
        message=message
    )


@app.route("/join")
def join_page():
    return render_template_string(JOIN_HTML)


@app.route("/join-qr")
def join_qr():
    payload = url_for("join_page", _external=True)

    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return send_file(buf, mimetype="image/png")


@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not email:
        email = None

    terms = 1 if request.form.get("terms") == "1" else 0
    marketing = 1 if request.form.get("marketing") == "1" else 0

    if not name or not phone or not terms:
        return redirect(url_for("home", message="Συμπλήρωσε όνομα, κινητό και αποδοχή όρων"))

    conn = get_db()

    if email:
        existing = conn.execute(
            "SELECT * FROM customers WHERE phone = ? OR email = ?",
            (phone, email)
        ).fetchone()
    else:
        existing = conn.execute(
            "SELECT * FROM customers WHERE phone = ?",
            (phone,)
        ).fetchone()

    if existing:
        conn.close()
        return redirect(url_for("deliver_card", token=existing["card_token"]))

    created_at = now_str()
    token = ensure_unique_token(conn)
    marketing_at = created_at if marketing else None

    cur = conn.execute("""
        INSERT INTO customers (
            card_token, name, phone, email, stamps,
            terms_accepted, marketing_consent,
            terms_accepted_at, marketing_consent_at, created_at
        )
        VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
    """, (
        token,
        name,
        phone,
        email,
        terms,
        marketing,
        created_at,
        marketing_at,
        created_at
    ))

    customer_id = cur.lastrowid

    conn.execute(
        "INSERT INTO history (customer_id, action, created_at) VALUES (?, ?, ?)",
        (customer_id, "Εγγραφή πελάτη", created_at)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("deliver_card", token=token))


@app.route("/deliver/<token>")
def deliver_card(token):
    customer = get_customer_by_token(token)
    if not customer:
        return "Ο πελάτης δεν βρέθηκε", 404

    return render_template_string(DELIVER_HTML, customer=customer)


@app.route("/search", methods=["POST"])
def search():
    phone = request.form.get("phone", "").strip()
    if not phone:
        return redirect(url_for("home"))

    conn = get_db()
    customer = conn.execute(
        "SELECT card_token FROM customers WHERE phone = ?",
        (phone,)
    ).fetchone()
    conn.close()

    if customer:
        return redirect(url_for("card_page", token=customer["card_token"]))

    return redirect(url_for("home", message="Δεν βρέθηκε πελάτης"))


@app.route("/card/<token>")
def card_page(token):
    conn = get_db()

    customer = conn.execute(
        "SELECT * FROM customers WHERE card_token = ?",
        (token,)
    ).fetchone()

    if not customer:
        conn.close()
        return "Ο πελάτης δεν βρέθηκε", 404

    total_coffees, total_gifts = get_customer_stats(conn, customer["id"])
    history = get_current_cycle_history(conn, customer["id"])
    conn.close()

    return render_template_string(
        CUSTOMER_HTML,
        customer=customer,
        customer_id=customer["id"],
        stamps=customer["stamps"],
        target=TARGET,
        history=history,
        total_coffees=total_coffees,
        total_gifts=total_gifts
    )


@app.route("/cashier-login", methods=["GET", "POST"])
def cashier_login():
    if cashier_logged_in():
        return redirect(url_for("scanner"))

    if request.method == "POST":
        pin = request.form.get("pin", "")
        if pin == CASHIER_PIN:
            session["cashier_auth"] = True
            return redirect(url_for("scanner"))
        return render_template_string(PIN_HTML, error="Λάθος PIN")

    return render_template_string(PIN_HTML, error="")


@app.route("/cashier-logout")
def cashier_logout():
    session.pop("cashier_auth", None)
    return redirect(url_for("cashier_login"))


@app.route("/scanner")
def scanner():
    if not cashier_logged_in():
        return redirect(url_for("cashier_login"))
    return render_template_string(SCANNER_HTML)


@app.route("/cashier/card/<token>")
def cashier_page(token):
    if not cashier_logged_in():
        return redirect(url_for("cashier_login"))

    customer = get_customer_by_token(token)
    if not customer:
        return "Ο πελάτης δεν βρέθηκε", 404

    return render_template_string(
        CASHIER_HTML,
        customer=customer,
        stamps=customer["stamps"],
        target=TARGET
    )


@app.route("/add/<token>/<int:amount>", methods=["POST"])
def add_stamps(token, amount):
    if not cashier_logged_in():
        return redirect(url_for("cashier_login"))

    if amount not in [1, 2, 3, 4, 5]:
        return "Μη έγκυρος αριθμός καφέδων", 400

    conn = get_db()
    customer = conn.execute(
        "SELECT * FROM customers WHERE card_token = ?",
        (token,)
    ).fetchone()

    if not customer:
        conn.close()
        return "Ο πελάτης δεν βρέθηκε", 404

    current_stamps = int(customer["stamps"])
    total = current_stamps + amount

    rewards_earned = total // TARGET
    new_stamps = total % TARGET

    conn.execute(
        "UPDATE customers SET stamps = ? WHERE id = ?",
        (new_stamps, customer["id"])
    )

    action_text = f"+{amount} καφές" if amount == 1 else f"+{amount} καφέδες"
    conn.execute(
        "INSERT INTO history (customer_id, action, created_at) VALUES (?, ?, ?)",
        (customer["id"], action_text, now_str())
    )

    for _ in range(rewards_earned):
        conn.execute(
            "INSERT INTO history (customer_id, action, created_at) VALUES (?, ?, ?)",
            (customer["id"], "Αυτόματο δώρο", now_str())
        )

    conn.commit()
    conn.close()

    return redirect(url_for("scanner"))


@app.route("/delete/<token>", methods=["GET", "POST"])
def delete_customer(token):
    if not cashier_logged_in():
        return redirect(url_for("cashier_login"))

    customer = get_customer_by_token(token)
    if not customer:
        return "Ο πελάτης δεν βρέθηκε", 404

    if request.method == "GET":
        return render_template_string(DELETE_HTML, error="")

    delete_password = request.form.get("delete_password", "")
    if delete_password != DELETE_PASSWORD:
        return render_template_string(DELETE_HTML, error="Λάθος κωδικός διαγραφής")

    conn = get_db()
    conn.execute("DELETE FROM history WHERE customer_id = ?", (customer["id"],))
    conn.execute("DELETE FROM customers WHERE id = ?", (customer["id"],))
    conn.commit()
    conn.close()

    return redirect(url_for("home", message="Ο πελάτης διαγράφηκε"))


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

    for row in rows:
        action = row["action"]

        if action.startswith("+"):
            try:
                total_added += int(action[1])
            except Exception:
                pass

        if action == "Αυτόματο δώρο":
            total_redeems += 1

    return render_template_string(
        ADMIN_HTML,
        customers=customers,
        total_customers=len(customers),
        total_added=total_added,
        total_redeems=total_redeems
    )


@app.route("/qr/<token>")
def qr(token):
    customer = get_customer_by_token(token)
    if not customer:
        return "Ο πελάτης δεν βρέθηκε", 404

    payload = url_for("card_page", token=token, _external=True)

    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return send_file(buf, mimetype="image/png")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

