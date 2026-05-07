from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps


def get_db_connection():
    db = Path(__file__).parent / "counter-roll.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({'error': 'Please log in first'}), 401
        return f(*args, **kwargs)
    return decorated_function


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

        return redirect(url_for("front_page"))

    return render_template("index.html", first=True)


@app.route("/front-page")
@login_required
def front_page():
    conn = get_db_connection()
    cases = conn.execute("SELECT * FROM cases").fetchall()
    conn.close()
    return render_template("front-page.html", cases=cases)


@app.route("/sign-up", methods=["GET", "POST"])
def sign_up():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        username = request.form.get("username")

        try:
            age = int(request.form.get("age"))
        except (TypeError, ValueError):
            return render_template("sign_up.html", mistake="Please enter a valid age")

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
                mistake="Underage! Come back when you become legal",
            )

        elif emails is not None:
            conn.close()
            return render_template(
                "sign_up.html", mistake="This e-mail already has an account registered"
            )

        elif usernames is not None:
            conn.close()
            return render_template("sign_up.html", mistake="Username taken")

        hashed_password = generate_password_hash(password)

        conn.execute(
            "INSERT INTO Accounts (email, password, username, age) VALUES (?, ?, ?, ?)",
            (email, hashed_password, username, age),
        )
        conn.commit()

        user = conn.execute(
            "SELECT * FROM Accounts WHERE email = ?", (email,)
        ).fetchone()

        conn.close()

        session["user_id"] = user["id"]
        session["username"] = user["username"]

        return redirect(url_for("front_page"))

    return render_template("sign_up.html")


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    

    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM Accounts WHERE id = ?", (session["user_id"],)
    ).fetchone()

    mistake = None  # for update errors

    if request.method == "POST":
        # --- existing update logic ---
        username = request.form.get("username")
        new_password = request.form.get("new_password")
        new_password_2 = request.form.get("new_password_2")
        password = request.form.get("password")

        if len(username) == 0:
            new_username = user["username"]
        if len(new_password) == 0:
            new_hashed = user["password"]

        if len(username) != 0:
            if not check_password_hash(user["password"], password):
                return render_template(
                    "profile.html", mistake="Wrong password on confirm", user=user
                )
            else:
                new_username = username
        if len(new_password) != 0:
            if new_password != new_password_2:
                return render_template(
                    "profile.html",
                    mistake="2nd password must match the first one",
                    user=user,
                )
            elif not check_password_hash(user["password"], password):
                return render_template(
                    "profile.html", mistake="Wrong password on confirm", user=user
                )
            else:
                new_hashed = generate_password_hash(new_password)

        conn.execute(
            "UPDATE Accounts SET username = ?, password = ? WHERE id = ?",
            (new_username, new_hashed, session["user_id"]),
        )
        conn.commit()

        # After successful update, redirect to front_page (no changes needed)
        return redirect(url_for("front_page"))

    # GET request: check for the 'deleted' query parameter
    deleted_param = request.args.get("deleted")
    # Convert the string 'False' to a real boolean False, otherwise None
    deleted = False if deleted_param == "False" else None

    conn.close()
    return render_template("profile.html", user=user, mistake=mistake, deleted=deleted)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/<int:case_id>")
@login_required
def case_show(case_id):
    
    conn = get_db_connection()
    items = conn.execute(
        "SELECT items.*, weapons.name  as weapon_name, rarities.rarity as rarity FROM items LEFT JOIN weapons ON items.weapon_id = weapons.id LEFT JOIN rarities ON items.rarity_id = rarities.id WHERE items.case_id = ?",
        (case_id,),
    ).fetchall()
    case = conn.execute(
        "SELECT * FROM cases WHERE id = ?",
        (case_id,),
    ).fetchone()
    conn.close()

    return render_template("case_display.html", items=items, case=case,  user_id=session["user_id"])

@app.route("/inventory")
def inventory():
    if "user_id" not in session:
        return redirect(url_for("home"))
    conn = get_db_connection()
    items = conn.execute(
        """SELECT items.*, weapons.name AS weapon_name, rarities.rarity AS rarity
           FROM inventory
           JOIN items    ON inventory.item_id   = items.id
           LEFT JOIN weapons  ON items.weapon_id  = weapons.id
           LEFT JOIN rarities ON items.rarity_id  = rarities.id
           WHERE inventory.account_id = ?""",
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("inventory.html", items=items)


@app.route("/api/open-case/<int:case_id>", methods=["POST"])
@login_required
def open_case(case_id):
    RARITY_WEIGHTS = {
        "Consumer Grade":   7979,
        "Industrial Grade": 1598,
        "Mil-Spec":         361,
        "Restricted":       58,
        "Classified":       11,
        "Covert":           2,
        "Knife":            0.26,
    }

    import random

    conn = get_db_connection()

    # Verify the case exists
    case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if case is None:
        conn.close()
        return jsonify({"error": "Case not found"}), 404

    # Load all items for this case with rarity names
    items = conn.execute(
        """SELECT items.*, weapons.name AS weapon_name, rarities.rarity AS rarity
           FROM items
           LEFT JOIN weapons  ON items.weapon_id  = weapons.id
           LEFT JOIN rarities ON items.rarity_id  = rarities.id
           WHERE items.case_id = ?""",
        (case_id,),
    ).fetchall()

    if not items:
        conn.close()
        return jsonify({"error": "No items in this case"}), 400

    # Group items by rarity
    by_rarity = {}
    for item in items:
        r = item["rarity"]
        by_rarity.setdefault(r, []).append(item)

    # Build weighted pool (only rarities that actually exist in this case)
    pool = [
        {"rarity": r, "items": item_list, "weight": RARITY_WEIGHTS.get(r, 1)}
        for r, item_list in by_rarity.items()
    ]

    total = sum(p["weight"] for p in pool)
    rand = random.uniform(0, total)
    chosen_group = pool[-1]
    for p in pool:
        rand -= p["weight"]
        if rand <= 0:
            chosen_group = p
            break

    won_item = random.choice(chosen_group["items"])

    # Persist to inventory
    conn.execute(
        "INSERT INTO inventory (account_id, item_id) VALUES (?, ?)",
        (session["user_id"], won_item["id"]),
    )
    conn.commit()
    conn.close()

    return jsonify({
        "id":     won_item["id"],
        "name":   won_item["name"],
        "weapon": won_item["weapon_name"],
        "rarity": won_item["rarity"],
        "image":  won_item["image"],
    })


@app.route("/delete-profile", methods=["POST"])
@login_required
def delete_profile():
    password = request.form.get("password")

    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM Accounts WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    if not check_password_hash(user["password"], password):
        conn.close()
        # Redirect with a query parameter indicating failure
        return redirect(url_for("profile", deleted=False))

    conn.execute(
        "DELETE FROM Accounts WHERE id = ?",
        (session["user_id"],)
    )
    conn.commit()
    conn.close()

    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
