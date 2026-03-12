from flask import Flask, render_template_string

app = Flask(__name__)

HTML = """
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
</div>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

if __name__ == "__main__":
    app.run(debug=True)
