from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash


def get_db_connection():
    db = Path(__file__).parent / "counter-roll.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


app = Flask(__name__)
app.secret_key = "debilsAnanas67"


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM Accounts WHERE email = ?", (email,)
        ).fetchone()

        conn.close()

        if user is None:
            return render_template("index.html", first=False)

        if not check_password_hash(user["password"], password):
            return render_template("index.html", first=False)
        
        session["user_id"] = user["id"]
        session["username"] = user["username"]

        return redirect(url_for("opening"))

    return render_template("index.html", first=True)


@app.route("/opening")
def opening():
    if "user_id" not in session:
        return redirect(url_for("home"))
    conn = get_db_connection()
    cases = conn.execute("SELECT * FROM cases").fetchall()
    conn.close()
    return render_template("opening-page.html", cases=cases)


@app.route("/sign-up", methods=["GET", "POST"])
def sign_up():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        username = request.form.get("username")

        try:
            age = int(request.form.get("age"))
        except (TypeError, ValueError):
            return render_template("sign_up.html", mistake="Lūdzu ievadi derīgu vecumu")

        conn = get_db_connection()

        emails = conn.execute(
            "SELECT * FROM Accounts WHERE email = ?", (email,)
        ).fetchone()

        usernames = conn.execute(
            "SELECT * FROM Accounts WHERE username = ?", (username,)
        ).fetchone()

        if age < 18:
            conn.close()
            return render_template(
                "sign_up.html",
                mistake="Nepietiekams vecums! Mēģini atkal, kad kļūsi vecāks",
            )

        elif emails is not None:
            conn.close()
            return render_template(
                "sign_up.html", mistake="Šim e-pastam jau ir reģistrēts lietotājs"
            )

        elif usernames is not None:
            conn.close()
            return render_template("sign_up.html", mistake="Lietotājvārds aizņemts")

        hashed_password = generate_password_hash(password)

        conn.execute(
            "INSERT INTO Accounts (email, password, username, age) VALUES (?, ?, ?, ?)",
            (email, hashed_password, username, age),
        )
        conn.commit()
        conn.close()

        user = conn.execute(
            "SELECT * FROM Accounts WHERE email = ?", (email,)
        ).fetchone()

        conn.close()

        session["user_id"] = user["id"]
        session["username"] = user["username"]

        return redirect(url_for("opening"))

    return render_template("sign_up.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
