from flask import Flask, render_template, url_for, redirect, session, request, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_dance.contrib.google import make_google_blueprint, google
import sqlite3
from dotenv import load_dotenv
import os

load_dotenv()

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback_secret')

app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')

# DB Setup 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "expensis.db")
DATABASE_DIR = os.path.join(BASE_DIR, "databases")

os.makedirs(DATABASE_DIR, exist_ok=True)

# ------------------ Database Functions ------------------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def save_user(name, email, picture):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            picture TEXT
        )
    """)
    cursor.execute(
        "INSERT OR IGNORE INTO users (name, email, picture) VALUES (?, ?, ?)",
        (name, email, picture)
    )
    conn.commit()
    conn.close()

def get_user_db(email):
    user_email_prefix = email.split('@')[0]
    db_path = os.path.join(DATABASE_DIR, f"{user_email_prefix}.db")
    os.makedirs(DATABASE_DIR, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            category TEXT,
            description TEXT,
            amount REAL    
        )
    """)
    conn.commit()
    return conn

# ------------------ Google OAuth ------------------
google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email"
    ],
    redirect_to="google_login"
)
app.register_blueprint(google_bp, url_prefix="/login")

# ------------------ Routes ------------------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        flash("Your message has been sent successfully!", "success")
        return redirect("/contact")
    return render_template("contact.html")

@app.route("/signin", methods=['GET', 'POST'])
def signin():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            stored_password = user["password"]
            if stored_password and check_password_hash(stored_password, password):
                session['user'] = {
                    "name": user["name"],
                    "email": user["email"],
                    "picture": user["picture"]
                }
                flash("Signed in successfully!", "success")
                return redirect(url_for("home"))
            else:
                flash("Invalid password!", "danger")
        else:
            flash("No account found with that email!", "warning")
        return redirect(url_for("signin"))
    return render_template("signin.html")

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users(name,email,password) VALUES (?, ?, ?)",
                (name, email, hashed_password)
            )
            conn.commit()
            conn.close()
            session['user'] = {"name": name, "email": email, "picture": None}

            flash("Sign up successful! You are now logged in.", "success")
            return redirect(url_for('home'))
        except sqlite3.IntegrityError:
            conn.close()
            flash("Username or Email already exists!", "danger")
            return redirect(url_for('signup'))
    return render_template("signup.html")

@app.route("/add_expense", methods=['GET', 'POST'])
def add_expense():
    if "user" not in session:
        flash("Please sign in!", "warning")
        return redirect('/signin')
    
    user_email = session["user"]["email"]
    conn = get_user_db(user_email)

    if request.method == "POST":
        date = request.form["date"]
        category = request.form["category"]
        description = request.form["description"]
        amount = request.form["amount"]

        conn.execute(
            "INSERT INTO expenses (date,category,description,amount) VALUES (?,?,?,?)",
            (date, category, description, amount)
        )
        conn.commit()
        conn.close()

        flash("Expense added successfully!", "success")
        return redirect(url_for("add_expense"))
    return render_template("add_expense.html")

@app.route("/show_expense")
def show_expense():
    return render_template("show_expense.html")

@app.route("/total_expenses")
def total_expense():
    if "user" not in session:
        flash("Please sign in!", "warning")
        return redirect(url_for("signin"))
    
    user_email = session["user"]["email"]
    conn = get_user_db(user_email)
    cursor = conn.cursor()

    time_period = request.args.get('time_period', 'day')
    
    if time_period == 'month':
        cursor.execute("SELECT strftime('%Y-%m', date) as time_group, category, SUM(amount) as total_amount FROM expenses GROUP BY time_group, category ORDER BY time_group DESC")
    elif time_period == 'year':
        cursor.execute("SELECT strftime('%Y', date) as time_group, category, SUM(amount) as total_amount FROM expenses GROUP BY time_group, category ORDER BY time_group DESC")
    else:
        cursor.execute("SELECT date, category, description, amount FROM expenses ORDER BY date DESC")
    
    expenses = cursor.fetchall()
    cursor.execute("SELECT SUM(amount) as total FROM expenses")
    total = cursor.fetchone()['total'] or 0
    conn.close()

    return render_template("total_expenses.html", expenses=expenses, total=total, time_period=time_period)

@app.route("/view_analysis")
def view_analysis():
    return render_template("view_analysis.html")

@app.route("/api/analysis_data")
def analysis_data():
    if "user" not in session:
        return jsonify({"error": "User not authenticated"}), 401

    user_email = session["user"]["email"]
    conn = get_user_db(user_email)
    cursor = conn.cursor()
    time_period = request.args.get("time_period", "day")
    
    line_labels, line_data = [], []
    category_labels, category_amounts = [], []

    if time_period == "day":
        cursor.execute("SELECT date, SUM(amount) as total_amount FROM expenses WHERE date BETWEEN date('now', '-7 day') AND date('now') GROUP BY date ORDER BY date ASC")
        results = cursor.fetchall()
        line_labels = [row['date'] for row in results]
        line_data = [row['total_amount'] for row in results]
        
        cursor.execute("SELECT category, SUM(amount) as total_amount FROM expenses WHERE date BETWEEN date('now', '-7 day') AND date('now') GROUP BY category ORDER BY total_amount DESC")
        category_results = cursor.fetchall()
        category_labels = [row['category'] for row in category_results]
        category_amounts = [row['total_amount'] for row in category_results]

    elif time_period == "week":
        cursor.execute("SELECT strftime('%Y-W%W', date) as time_group, SUM(amount) as total_amount FROM expenses WHERE date BETWEEN date('now', '-2 months') AND date('now') GROUP BY time_group ORDER BY time_group ASC")
        results = cursor.fetchall()
        line_labels = [row['time_group'] for row in results]
        line_data = [row['total_amount'] for row in results]

        cursor.execute("SELECT category, SUM(amount) as total_amount FROM expenses WHERE date BETWEEN date('now', '-2 months') AND date('now') GROUP BY category ORDER BY total_amount DESC")
        category_results = cursor.fetchall()
        category_labels = [row['category'] for row in category_results]
        category_amounts = [row['total_amount'] for row in category_results]

    elif time_period == "month":
        cursor.execute("SELECT strftime('%Y-%m', date) as time_group, SUM(amount) as total_amount FROM expenses WHERE date BETWEEN date('now', '-1 year') AND date('now') GROUP BY time_group ORDER BY time_group ASC")
        results = cursor.fetchall()
        line_labels = [row['time_group'] for row in results]
        line_data = [row['total_amount'] for row in results]

        cursor.execute("SELECT category, SUM(amount) as total_amount FROM expenses WHERE date BETWEEN date('now', '-1 year') AND date('now') GROUP BY category ORDER BY total_amount DESC")
        category_results = cursor.fetchall()
        category_labels = [row['category'] for row in category_results]
        category_amounts = [row['total_amount'] for row in category_results]

    elif time_period == "year":
        cursor.execute("SELECT strftime('%Y', date) as time_group, SUM(amount) as total_amount FROM expenses GROUP BY time_group ORDER BY time_group ASC")
        results = cursor.fetchall()
        line_labels = [row['time_group'] for row in results]
        line_data = [row['total_amount'] for row in results]

        cursor.execute("SELECT category, SUM(amount) as total_amount FROM expenses GROUP BY category ORDER BY total_amount DESC")
        category_results = cursor.fetchall()
        category_labels = [row['category'] for row in category_results]
        category_amounts = [row['total_amount'] for row in category_results]

    conn.close()
    
    return jsonify({
        "line_chart": {
            "labels": line_labels,
            "amounts": line_data
        },
        "category_charts": {
            "labels": category_labels,
            "amounts": category_amounts
        }
    })

# ------------------ Google Login Callback ------------------
@app.route("/google_login")
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return "Failed to fetch user info from Google."

    user_info = resp.json()
    email = user_info.get("email")
    name = user_info.get("name")
    picture = user_info.get("picture")

    save_user(name, email, picture)
    session["user"] = {"name": name, "email": email, "picture": picture}

    return redirect(url_for("home"))

# ------------------ Profile & Logout ------------------
@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect(url_for("signin"))
    return render_template("profile.html", user=session["user"])

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
