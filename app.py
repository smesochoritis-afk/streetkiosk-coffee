from flask import Flask, render_template_string, send_file, redirect, url_for, request
import qrcode
import io

app = Flask(__name__)

TARGET = 5

customers = {}
next_customer_id = 1


REGISTER_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STREETKIOSK - Εγγραφή Πελάτη</title>
    <style>
        body{
            font-family: Arial, sans-serif;
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
            width:360px;
            padding:30px;
            border-radius:16px;
            box-shadow:0 5px 20px rgba(0,0,0,0.15);
        }
        h1{
            text-align:center;
            margin-top:0;
            font-size:26px;
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
            font-size:17px;
            cursor:pointer;
        }
        .list{
            margin-top:20px;
            padding-top:15px;
            border-top:1px solid #eee;
        }
        .customer-item{
            margin-bottom:10px;
            padding:10px;
            background:#fafafa;
            border-radius:10px;
        }
        .customer-item a{
            text-decoration:none;
            color:#222;
            font-weight:bold;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>☕ STREETKIOSK</h1>
        <p>Εγγραφή νέου πελάτη</p>

        <form method="post" action="/register">
            <input type="text" name="name" placeholder="Όνομα πελάτη" required>
            <input type="text" name="phone" placeholder="Κινητό" required>
            <input type="email" name="email" placeholder="Email (προαιρετικό)">
            <button type="submit">Δημιουργία κάρτας</button>
        </form>

        <div class="list">
            <strong>Πελάτες:</strong>
            {% if customers %}
                {% for cid, customer in customers.items() %}
                    <div class="customer-item">
                        <a href="/customer/{{ cid }}">{{ customer["name"] }}</a><br>
                        {{ customer["phone"] }}
                    </div>
                {% endfor %}
            {% else %}
                <div class="customer-item">Δεν υπάρχουν πελάτες ακόμα.</div>
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
            font-family: Arial, sans-serif;
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
            width:340px;
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
            font-family: Arial, sans-serif;
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
    <meta http-equiv="refresh" content="1.5;url=/cashier/{{ customer_id }}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Αποτέλεσμα</title>
    <style>
        body{
            font-family: Arial, sans-serif;
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

@app.route("/")
def home():
    return render_template_string(REGISTER_HTML, customers=customers)

@app.route("/register", methods=["POST"])
def register():
    global next_customer_id

    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()

    if not name or not phone:
        return redirect(url_for("home"))

    customer_id = str(next_customer_id)
    next_customer_id += 1

    customers[customer_id] = {
        "name": name,
        "phone": phone,
        "email": email,
        "stamps": 0
    }

    return redirect(url_for("customer_card", customer_id=customer_id))

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

@app.route("/cashier/<customer_id>")
def cashier(customer_id):
    customer = customers.get(customer_id)
    if not customer:
        return "Ο πελάτης δεν βρέθηκε", 404

    return render_template_string(
        CASHIER_HTML,
        customer=customer,
        customer_id=customer_id,
        stamps=customer["stamps"],
        target=TARGET
    )

@app.route("/add/<customer_id>/<int:amount>", methods=["POST"])
def add_stamps(customer_id, amount):
    customer = customers.get(customer_id)
    if not customer:
        return "Ο πελάτης δεν βρέθηκε", 404

    customer["stamps"] += amount
    if customer["stamps"] > TARGET:
        customer["stamps"] = TARGET

    if customer["stamps"] >= TARGET:
        message = "Έφτασε δώρο 🎁"
    else:
        message = f"Προστέθηκαν {amount} καφέδες ☕"

    return render_template_string(
        RESULT_HTML,
        message=message,
        stamps=customer["stamps"],
        target=TARGET,
        customer_id=customer_id
    )

@app.route("/redeem/<customer_id>", methods=["POST"])
def redeem(customer_id):
    customer = customers.get(customer_id)
    if not customer:
        return "Ο πελάτης δεν βρέθηκε", 404

    if customer["stamps"] < TARGET:
        message = "Δεν υπάρχει ακόμα δώρο"
    else:
        customer["stamps"] = 0
        message = "Το δώρο εξαργυρώθηκε ✅"

    return render_template_string(
        RESULT_HTML,
        message=message,
        stamps=customer["stamps"],
        target=TARGET,
        customer_id=customer_id
    )

@app.route("/qr/<customer_id>")
def qr(customer_id):
    customer = customers.get(customer_id)
    if not customer:
        return "Ο πελάτης δεν βρέθηκε", 404

    url = "https://streetkiosk-coffee-1.onrender.com/cashier/" + customer_id

    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return send_file(buf, mimetype="image/png")

if __name__ == "__main__":
    app.run(debug=True)
