from flask import Flask, render_template_string, send_file, redirect, url_for
import qrcode
import io

app = Flask(__name__)

TARGET = 5

customers = {
    "demo": {"name": "Demo Customer", "stamps": 0}
}

CUSTOMER_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Κάρτα Πελάτη</title>

<style>
body{
    font-family: Arial;
    background:#f4f4f4;
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:100vh;
    margin:0;
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
    margin-bottom:16px;
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
</style>
</head>

<body>

<div class="card">

<div class="title">☕ STREETKIOSK</div>
<div class="name">{{ customer["name"] }}</div>

<div class="stamps">

<div class="stamp {% if stamps >= 1 %}filled{% endif %}">
{% if stamps >= 1 %}✔{% else %}1{% endif %}
</div>

<div class="stamp {% if stamps >= 2 %}filled{% endif %}">
{% if stamps >= 2 %}✔{% else %}2{% endif %}
</div>

<div class="stamp {% if stamps >= 3 %}filled{% endif %}">
{% if stamps >= 3 %}✔{% else %}3{% endif %}
</div>

<div class="stamp {% if stamps >= 4 %}filled{% endif %}">
{% if stamps >= 4 %}✔{% else %}4{% endif %}
</div>

<div class="stamp {% if stamps >= 5 %}filled{% endif %}">
{% if stamps >= 5 %}✔{% else %}5{% endif %}
</div>

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

<a class="btn" href="/cashier/{{ customer_id }}">Ταμείο</a>

</div>

</body>
</html>
"""

@app.route("/")
def home():
    return redirect(url_for("customer_card", customer_id="demo"))

@app.route("/customer/<customer_id>")
def customer_card(customer_id):

    customer = customers.get(customer_id)

    if not customer:
        return "Ο πελάτης δεν βρέθηκε"

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
        return "Ο πελάτης δεν βρέθηκε"

    return f"""
    <h1>STREETKIOSK Ταμείο</h1>

    <p>Πελάτης: {customer["name"]}</p>
    <p>Σφραγίδες: {customer["stamps"]}/{TARGET}</p>

    <a href="/add/{customer_id}/1">+1 Καφές</a><br><br>
    <a href="/add/{customer_id}/2">+2 Καφέδες</a><br><br>
    <a href="/add/{customer_id}/3">+3 Καφέδες</a><br><br>

    <a href="/customer/{customer_id}">Πίσω στην κάρτα</a>
    """
@app.route("/add/<customer_id>/<int:amount>")
def add_stamps(customer_id, amount):

    customer = customers.get(customer_id)

    if not customer:
        return "Ο πελάτης δεν βρέθηκε"

    new_total = customer["stamps"] + amount

    if customer["stamps"] >= TARGET:
        customer["stamps"] = 0
    elif new_total > TARGET:
        customer["stamps"] = 0
    else:
        customer["stamps"] = new_total

    return redirect(url_for("cashier", customer_id=customer_id))

@app.route("/qr/<customer_id>")
def qr(customer_id):

    url = f"https://streetkiosk-coffee.onrender.com/cashier/{customer_id}"

    img = qrcode.make(url)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return send_file(buf, mimetype="image/png")

if __name__ == "__main__":
    app.run(debug=True)
