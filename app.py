from flask import Flask, render_template_string, send_file
import qrcode
import io

app = Flask(__name__)

stamps = 0
TARGET = 5


HOME_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>StreetKiosk Coffee</title>

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
    width:320px;
    text-align:center;
}

.title{
    font-size:26px;
    font-weight:bold;
}

.stamps{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:15px;
    margin-top:20px;
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
}

.filled{
    background:#222;
    color:white;
}

.reward{
    background:gold;
    border:3px solid #caa400;
}

.btn{
    display:inline-block;
    margin-top:20px;
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
<p>Κάρτα Καφέ</p>

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

<p>
{% if stamps >= target %}
Έχεις δωρεάν καφέ 🎉
{% else %}
Έχεις {{ stamps }}/{{ target }} σφραγίδες
{% endif %}
</p>

<a class="btn" href="/cashier">Ταμείο</a>

</div>

</body>
</html>
"""


CASHIER_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<title>Cashier</title>

<style>

body{
font-family:Arial;
background:#f4f4f4;
display:flex;
justify-content:center;
align-items:center;
height:100vh;
margin:0;
}

.panel{
background:white;
padding:30px;
border-radius:16px;
box-shadow:0 5px 20px rgba(0,0,0,0.15);
width:340px;
text-align:center;
}

.qr{
margin-top:20px;
}

</style>
</head>

<body>

<div class="panel">

<h2>☕ STREETKIOSK</h2>
<p>Ταμείο</p>

<div class="qr">
<img src="/qr" width="180">
</div>

<br>

<a href="/">Επιστροφή</a>

</div>

</body>
</html>
"""


RESULT_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Scan</title>

<style>

body{
font-family:Arial;
background:#f4f4f4;
display:flex;
justify-content:center;
align-items:center;
height:100vh;
margin:0;
}

.box{
background:white;
padding:30px;
border-radius:16px;
box-shadow:0 5px 20px rgba(0,0,0,0.15);
text-align:center;
}

.btn{
display:inline-block;
margin-top:20px;
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

<h2>{{ message }}</h2>
<p>{{ stamps }}/{{ target }} σφραγίδες</p>

<a class="btn" href="/">Πίσω στην κάρτα</a>

</div>

</body>
</html>
"""


@app.route("/")
def home():
    global stamps
    return render_template_string(HOME_HTML, stamps=stamps, target=TARGET)


@app.route("/cashier")
def cashier():
    return render_template_string(CASHIER_HTML)


@app.route("/qr")
def qr():

    url = "https://streetkiosk-coffee.onrender.com/scan"

    img = qrcode.make(url)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return send_file(buf, mimetype="image/png")


@app.route("/scan")
def scan():

    global stamps

    if stamps < TARGET:
        stamps += 1

    if stamps >= TARGET:
        message = "Δωρεάν καφές!"
    else:
        message = "Προστέθηκε 1 καφές ☕"

    return render_template_string(
        RESULT_HTML,
        message=message,
        stamps=stamps,
        target=TARGET
    )


if __name__ == "__main__":
    app.run(debug=True)
