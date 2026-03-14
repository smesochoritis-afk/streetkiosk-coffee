from flask import Flask, render_template_string, send_file, redirect, url_for, request
import qrcode
import io
from datetime import datetime

app = Flask(__name__)

TARGET = 5
ADMIN_PIN = "2580"

customers = {}
next_customer_id = 1


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
    padding:20px;
}
.card{
    background:white;
    width:380px;
    padding:30px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15);
}
h1{
    text-align:center;
    margin-top:0;
}
p{
    text-align:center;
    color:#666;
}
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
.list{
    margin-top:20px;
    border-top:1px solid #eee;
    padding-top:12px;
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
.toplink{
    display:inline-block;
    margin-top:10px;
    text-decoration:none;
    color:#222;
    font-weight:bold;
}
.notice{
    margin-top:12px;
    padding:10px;
    background:#fff8e1;
    border:1px solid #f0d98a;
    border-radius:10px;
    font-size:14px;
    color:#6b5a00;
    text-align:center;
}
hr{
    margin:18px 0;
    border:none;
    border-top:1px solid #eee;
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
        <button type="submit">Δημιουργία κάρτας</button>
    </form>

    <hr>

    <form method="post" action="/search">
        <input type="text" name="phone" placeholder="Αναζήτηση πελάτη με κινητό">
        <button type="submit">Αναζήτηση</button>
    </form>

    <p><a class="toplink" href="/scanner">Άνοιγμα Scanner Ταμείου</a></p>

    <div class="list">
        <strong>Πελάτες:</strong>
        {% if customers %}
            {% for cid, customer in customers.items() %}
                <div class="customer">
                    <a href="/customer/{{ cid }}">{{ customer["name"] }}</a><br>
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
    padding:20px;
}
.card{
    background:white;
    padding:30px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15);
    width:360px;
    text-align:center;
}
.title{
    font-size:26px;
    font-weight:bold;
    margin-bottom:8px;
}
.name{
    color:#555;
    margin-bottom:6px;
    font-weight:bold;
}
.phone{
    color:#777;
    margin-bottom:16px;
    font-size:14px;
}
.stamps{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:15px;
    margin-top:20px;
    justify-items:center;
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
    background:white;
}
.filled{
    background:#222;
    color:white;
}
.reward{
    background:gold;
    border-color:#caa400;
}
.info{
    margin-top:18px;
    font-weight:bold;
}
.qrbox{
    margin-top:18px;
}
.btn{
    display:inline-block;
    margin-top:18px;
    padding:10px 14px;
    background:#222;
    color:white;
    text-decoration:none;
    border-radius:10px;
}
.btn2{
    display:inline-block;
    margin-top:10px;
    padding:10px 14px;
    background:#555;
    color:white;
    text-decoration:none;
    border-radius:10px;
}
.history{
    margin-top:20px;
    text-align:left;
    background:#fafafa;
    padding:12px;
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

    <a class="btn" href="/cashier/{{ customer_id }}">Ταμείο</a><br>
    <a class="btn2" href="/">Πίσω στην εγγραφή</a>

    <div class="history">
        <h3>Ιστορικό</h3>
        {% if customer["history"] %}
            {% for item in customer["history"]|reverse %}
                <div class="history-item">
                    {{ item["action"] }} | {{ item["date"] }} | {{ item["time"] }}
                </div>
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
<title>Admin PIN</title>
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
.error{
    color:#b00020;
    margin-top:10px;
}
</style>
</head>
<body>
<div class="box">
    <h2>Κωδικός Ταμείου</h2>
    <p>Βάλε τον admin PIN για να ανοίξει το ταμείο</p>

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
    width:360px;
    text-align:center;
}
.title{
    font-size:26px;
    font-weight:bold;
}
.name{
    margin-top:8px;
    color:#555;
    font-weight:bold;
}
.info{
    margin:16px 0;
    font-weight:bold;
}
.row{
    display:flex;
    gap:10px;
    margin-top:14px;
}
.row form{
    flex:1;
    margin:0;
}
.btn{
    width:100%;
    border:none;
    border-radius:12px;
    padding:14px 10px;
    font-size:18px;
    cursor:pointer;
}
.dark{
    background:#222;
    color:white;
}
.gold{
    background:gold;
    color:#222;
}
.red{
    background:#b00020;
    color:white;
}
.back{
    display:inline-block;
    margin-top:18px;
    color:#222;
    text-decoration:none;
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
            <input type="hidden" name="pin" value="{{ pin }}">
            <button class="btn dark" type="submit">+1</button>
        </form>
        <form method="post" action="/add/{{ customer_id }}/2">
            <input type="hidden" name="pin" value="{{ pin }}">
            <button class="btn dark" type="submit">+2</button>
        </form>
        <form method="post" action="/add/{{ customer_id }}/3">
            <input type="hidden" name="pin" value="{{ pin }}">
            <button class="btn dark" type="submit">+3</button>
        </form>
    </div>

    <div class="row">
        <form method="post" action="/redeem/{{ customer_id }}">
            <input type="hidden" name="pin" value="{{ pin }}">
            <button class="btn gold" type="submit">Εξαργύρωση Δώρου</button>
        </form>
    </div>

    <div class="row">
        <form method="post" action="/delete/{{ customer_id }}">
            <input type="hidden" name="pin" value="{{ pin }}">
            <button class="btn red" type="submit">Διαγραφή Πελάτη</button>
        </form>
    </div>

    <a class="back" href="/customer/{{ customer_id }}">Επιστροφή στην κάρτα</a>
</div>
</body>
</html>
"""

RESULT_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="1.5;url=/cashier/{{ customer_id }}?pin={{ pin }}">
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
    margin:0;
}
.box{
    background:white;
    padding:30px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15);
    width:320px;
    text-align:center;
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
    text-align:center;
}
.box{
    max-width:500px;
    margin:0 auto;
    background:white;
    padding:20px;
    border-radius:16px;
    box-shadow:0 5px 20px rgba(0,0,0,0.15);
}
#reader{
    width:100%;
    margin-top:20px;
}
.btn{
    display:inline-block;
    margin-top:14px;
    padding:10px 14px;
    background:#222;
    color:white;
    text-decoration:none;
    border-radius:10px;
}
</style>
</head>
<body>
<div class="box">
    <h2>📷 Scanner Πελάτη</h2>
    <p>Σκάναρε το QR του πελάτη για να ανοίξει το ταμείο του</p>
    <div id="reader"></div>
    <a class="btn" href="/">Πίσω</a>
</div>

<script>
function onScanSuccess(decodedText) {
    if (decodedText.includes("/customer/")) {
        const parts = decodedText.split("/customer/");
        const customerId = parts[1].split(/[?#]/)[0];
        window.location.href = "/cashier/" + customerId;
    } else if (decodedText.startsWith("customer:")) {
        const customerId = decodedText.split(":")[1];
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

@app.route("/")
def home():
    message = request.args.get("message", "")
    return render_template_string(
        REGISTER_HTML,
        customers=customers,
        target=TARGET,
        message=message
    )

@app.route("/register", methods=["POST"])
def register():
    global next_customer_id

    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not name or not phone:
        return redirect(url_for("home", message="Συμπλήρωσε όνομα και κινητό"))

    for cid, customer in customers.items():
        existing_phone = customer.get("phone", "").strip()
        existing_email = customer.get("email", "").strip().lower()

        same_phone = phone and existing_phone == phone
        same_email = email and existing_email == email

        if same_phone or same_email:
            return redirect(url_for("customer_card", customer_id=cid))

    customer_id = str(next_customer_id)
    next_customer_id += 1

    customers[customer_id] = {
        "name": name,
        "phone": phone,
        "email": email,
        "stamps": 0,
        "history": []
    }

    return redirect(url_for("customer_card", customer_id=customer_id))

@app.route("/search", methods=["POST"])
def search():
    phone = request.form.get("phone", "").strip()

    if not phone:
        return redirect(url_for("home"))

    for cid, customer in customers.items():
        if customer.get("phone", "").strip() == phone:
            return redirect(url_for("customer_card", customer_id=cid))

    return redirect(url_for("home", message="Δεν βρέθηκε πελάτης"))

@app.route("/customer/<customer_id>")
def customer_card(customer_id):
    customer = customers.get(customer_id)
    if not customer:
        return "Ο πελάτης δεν βρέθηκε", 404

    return render_template_string(
        CUSTOMER_HTML,
        customer=customer,
        customer_id=customer_id,
        stamps=customer["stamps"],
        target=TARGET
    )

@app.route("/cashier/<customer_id>", methods=["GET", "POST"])
def cashier(customer_id):
    customer = customers.get(customer_id)
    if not customer:
        return "Ο πελάτης δεν βρέθηκε", 404

    pin = request.values.get("pin", "")

    if pin != ADMIN_PIN:
        return render_template_string(PIN_HTML, error="Λάθος PIN")

    return render_template_string(
        CASHIER_HTML,
        customer=customer,
        customer_id=customer_id,
        stamps=customer["stamps"],
        target=TARGET,
        pin=pin
    )

@app.route("/add/<customer_id>/<int:amount>", methods=["POST"])
def add_stamps(customer_id, amount):
    customer = customers.get(customer_id)
    if not customer:
        return "Ο πελάτης δεν βρέθηκε", 404

    pin = request.form.get("pin", "")
    if pin != ADMIN_PIN:
        return "Μη εξουσιοδοτημένη πρόσβαση", 403

    customer["stamps"] += amount
    if customer["stamps"] > TARGET:
        customer["stamps"] = TARGET

    now = datetime.now()
    customer["history"].append({
        "action": f"+{amount} καφές" if amount == 1 else f"+{amount} καφέδες",
        "date": now.strftime("%d-%m-%Y"),
        "time": now.strftime("%H:%M")
    })

    if customer["stamps"] >= TARGET:
        message = "Έφτασε δώρο 🎁"
    else:
        message = f"Προστέθηκαν {amount} καφέδες ☕"

    return render_template_string(
        RESULT_HTML,
        message=message,
        stamps=customer["stamps"],
        target=TARGET,
        customer_id=customer_id,
        pin=pin
    )

@app.route("/redeem/<customer_id>", methods=["POST"])
def redeem(customer_id):
    customer = customers.get(customer_id)
    if not customer:
        return "Ο πελάτης δεν βρέθηκε", 404

    pin = request.form.get("pin", "")
    if pin != ADMIN_PIN:
        return "Μη εξουσιοδοτημένη πρόσβαση", 403

    now = datetime.now()

    if customer["stamps"] < TARGET:
        message = "Δεν υπάρχει ακόμα δώρο"
    else:
        customer["stamps"] = 0
        customer["history"].append({
            "action": "Εξαργύρωση δώρου",
            "date": now.strftime("%d-%m-%Y"),
            "time": now.strftime("%H:%M")
        })
        message = "Το δώρο εξαργυρώθηκε ✅"

    return render_template_string(
        RESULT_HTML,
        message=message,
        stamps=customer["stamps"],
        target=TARGET,
        customer_id=customer_id,
        pin=pin
    )

@app.route("/delete/<customer_id>", methods=["POST"])
def delete_customer(customer_id):
    pin = request.form.get("pin", "")

    if pin != ADMIN_PIN:
        return "Μη εξουσιοδοτημένη πρόσβαση", 403

    if customer_id in customers:
        del customers[customer_id]

    return redirect(url_for("home"))

@app.route("/scanner")
def scanner():
    return render_template_string(SCANNER_HTML)

@app.route("/qr/<customer_id>")
def qr(customer_id):
    customer = customers.get(customer_id)
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
