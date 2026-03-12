from flask import Flask, render_template_string, send_file
import qrcode
import io

app = Flask(__name__)

HOME_HTML = """
<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>StreetKiosk Coffee</title>

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
margin-bottom:10px;
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
margin:auto;
}

.reward{
background:gold;
border:3px solid #caa400;
}

.linkbtn{
display:inline-block;
margin-top:20px;
background:#222;
color:white;
text-decoration:none;
padding:10px 14px;
border-radius:10px;
}

</style>
</head>

<body>

<div class="card">

<div class="title">☕ STREETKIOSK</div>
<p>Κάρτα Καφέ</p>

<div class="stamps">

<div class="stamp">1</div>
<div class="stamp">2</div>
<div class="stamp">3</div>
<div class="stamp">4</div>
<div class="stamp">5</div>
<div class="stamp reward">🎁</div>

</div>

<a class="linkbtn" href="/cashier">Ταμείο</a>

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
<title>StreetKiosk Cashier</title>

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

.panel{
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
margin-bottom:10px;
}

.btn{
background:#222;
color:white;
border:none;
padding:14px 18px;
border-radius:12px;
font-size:18px;
cursor:pointer;
width:100%;
margin-top:20px;
}

.qrbox{
margin-top:20px;
padding:25px;
border:2px dashed #bbb;
border-radius:14px;
color:#666;
background:#fafafa;
}

.back{
display:inline-block;
margin-top:20px;
text-decoration:none;
color:#222;
}

</style>
</head>

<body>

<div class="panel">

<div class="title">☕ STREETKIOSK</div>
<p>Ταμείο</p>

<button class="btn">Νέα αγορά καφέ</button>

<div class="qrbox">
Εδώ θα εμφανίζεται το QR
</div>

<a class="back" href="/">Επιστροφή</a>

</div>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HOME_HTML)

@app.route("/cashier")
def cashier():
    return render_template_string(CASHIER_HTML)
    @app.route("/qr")
def qr():

    url = "https://streetkiosk-coffee.onrender.com"

    img = qrcode.make(url)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return send_file(buf, mimetype="image/png")

if __name__ == "__main__":
    app.run(debug=True)
