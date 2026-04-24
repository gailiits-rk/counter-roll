from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from pathlib import Path
from werkzeug.security import check_password_hash

def get_db_connection():
    db = Path(__file__).parent / "counter-roll.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


app = Flask(__name__)
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db_connection()

        # Get user by email
        user = conn.execute(
            "SELECT * FROM Accounts WHERE email = ? AND password = ?",
            (email,password)
        ).fetchone()

        conn.close()
        if user == None:
            return render_template("index.html", first = False)   
        else:
            return redirect(url_for("opening"))
    
    return render_template("index.html", first = True)

@app.route("/opening")
def opening():
    conn = get_db_connection()
    cases = conn.execute("SELECT * FROM cases").fetchall()
    conn.close()
    return render_template("opening-page.html", cases=cases)

@app.route("/sign-up")
def sign_up():
    return render_template("sign_up.html")


if __name__ == "__main__":
    app.run(debug=True)