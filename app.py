from turtle import position
from flask import Flask, render_template, request, redirect, session, flash, send_file
import sqlite3
import io
conn = sqlite3.connect("database.db")
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS userdata(user TEXT, data TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS users(username TEXT, password TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS logs(user TEXT, action TEXT)")

conn.commit()
conn.close()

import sqlite3
import hashlib
import os
from cryptography.fernet import Fernet
import bcrypt


app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- ENCRYPTION ----------------
import os

KEY_FILE = "secret.key"

if not os.path.exists(KEY_FILE):
    key = b'12345678901234567890123456789012'
else:
    with open(KEY_FILE, "rb") as f:
        key = f.read()

cipher = Fernet(key)
def encrypt_data(text):
    return cipher.encrypt(text.encode()).decode()

def decrypt_data(text):
    return cipher.decrypt(text.encode()).decode()

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS userdata(
        id INTEGER PRIMARY KEY,
        owner TEXT,
        encrypted_data TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("home.html")



# ---------- REGISTER ----------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        u=request.form["username"]
        p=request.form["password"]

        conn=sqlite3.connect("database.db")
        c=conn.cursor()
        hashed = hashlib.sha256(p.encode()).hexdigest()
        c.execute("INSERT INTO users VALUES(?,?)",(u,hashed))


        conn.commit()
        conn.close()
        return redirect("/login")
    return render_template("register.html")

# ---------- LOGIN ----------
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        hashed = hashlib.sha256(p.encode()).hexdigest()

        c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, hashed))
        user = c.fetchone()

        conn.close()

        if user:
            session["user"] = u
            return redirect("/dashboard")
        else:
            return "Invalid Login"

    return render_template("login.html")
# ---------- DASHBOARD ----------

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT rowid, data FROM userdata WHERE user=?", (session["user"],))
    data = c.fetchall()

    conn.close()

    return render_template("dashboard.html", data=data)
# ---------- UPLOAD ----------
@app.route("/upload", methods=["GET","POST"])
def upload():
    if request.method == "POST":
        data = request.form.get("data")
        file = request.files.get("file")
        allowed = ["txt","pdf","jpg","png"]

        if file:
            ext = file.filename.split(".")[-1]
            if ext not in allowed:
                return "File type not allowed"

            consent = request.form.get("consent")

            if consent != "yes":
                return "Consent Required"

            if file and file.filename != "":
                file.save("uploads/" + file.filename)

        enc = encrypt_data(data)

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO userdata VALUES(?,?)",(session["user"], enc))

        conn.commit()
        conn.close()

        flash("File uploaded successfully!")
        return redirect("/upload")
    return render_template("upload.html")




# ---------- ADMIN ----------
@app.route("/admin")
def admin():

    search = request.args.get("search")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    if search:
        c.execute("SELECT rowid, user, data FROM userdata WHERE user LIKE ?",('%'+search+'%',))
    else:
        c.execute("SELECT rowid, user, data FROM userdata")

    data = c.fetchall()

    conn.close()

    return render_template("admin.html", data=data)


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------- DELETE ----------
@app.route("/delete/<int:id>")
def delete(id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("DELETE FROM userdata WHERE rowid=?",(id,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ---------------- RUN ----------------
@app.route("/download/<int:id>")
def download_file(id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT data FROM userdata WHERE rowid=?", (id,))
    row = c.fetchone()
    conn.close()

    if row:
        encrypted_data = row[0]

        return send_file(
            io.BytesIO(encrypted_data.encode()),
            as_attachment=True,
            download_name=f"encrypted_{id}.txt",
            mimetype="text/plain"
        )

    return "File not found"
@app.route("/profile")
def profile():
    user = session.get("user")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM userdata WHERE user=?", (user,))
    count = c.fetchone()[0]

    conn.close()

    return render_template("profile.html", user=user, count=count)


# ---------------- download ----------------

@app.route("/test")
def test():
    return "TEST WORKING"

@app.route("/hello")
def hello():
    return "HELLO WORKING"

@app.route("/decrypt/<int:id>")
def decrypt_record(id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT data FROM userdata WHERE rowid=?", (id,))
    row = c.fetchone()
    conn.close()

    original = decrypt_data(row[0])

    return f"""
    <html>
    <head>
    <style>
    body{{
        background:#f1f5f9;
        display:flex;
        justify-content:center;
        align-items:center;
        height:100vh;
        font-family:Arial;
    }}

    .card{{
        background:white;
        width:340px;
        padding:30px;
        border-radius:18px;
        text-align:center;
        box-shadow:0 10px 25px rgba(0,0,0,0.2);
    }}

    .avatar{{
        width:90px;
        height:90px;
        background:#2563eb;
        border-radius:50%;
        margin:0 auto 15px;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:36px;
        color:white;
    }}

    .subtitle{{
        color:#555;
        font-size:14px;
        margin-bottom:15px;
    }}

    .data-box{{
        background:#e5e7eb;
        colour:black;
        padding:15px;
        border-radius:12px;
        word-wrap:break-word;
        margin:15px 0;
        font-size:14px;
    }}

    button{{
        background:#2563eb;
        color:white;
        padding:8px 16px;
        border:none;
        border-radius:6px;
        cursor:pointer;
    }}

    a{{
        display:block;
        margin-top:18px;
        text-decoration:none;
        color:black;
    }}
    </style>

    <script>
    function toggleMask(){{
        var box = document.getElementById("box");
        var real = document.getElementById("real").innerText;

        if(box.innerText === "************"){{
            box.innerText = real;
        }} else {{
            box.innerText = "************";
        }}
    }}
    </script>
    </head>

    <body>

    <div class="card">

        <div class="avatar">🔐</div>

        <h2>Decrypted Data</h2>

        <p class="subtitle">Secure Cloud User</p>

        <div id="box" class="data-box">************</div>

        <div id="real" style="display:none;">{original}</div>

        <button onclick="toggleMask()">Show / Hide</button>

        <a href="/dashboard">← Back to Dashboard</a>

    </div>

    </body>
    </html>
    """



if __name__ == "__main__":
    app.run(debug=True)

    
