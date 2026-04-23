from flask import Flask, render_template
import sqlite3
from pathlib import Path

def get_db_connection():
    db = Path(__file__).parent / "counter-roll.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


app = Flask(__name__)
@app.route("/")
def home():
    conn = get_db_connection()
    cases = conn.execute("SELECT * FROM cases").fetchall()
    conn.close()
    return render_template("index.html", cases=cases)

if __name__ == "__main__":
    app.run(debug=True)