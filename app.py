from flask import Flask, render_template, url_for, redirect, session, request, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_dance.contrib.google import make_google_blueprint, google
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback_secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ------------------ Database Models ------------------
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=True)
    picture = db.Column(db.String(300))


class Expense(db.Model):
    __tablename__ = "expense"
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), db.ForeignKey("users.email"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(100))
    description = db.Column(db.String(300))
    amount = db.Column(db.Float)


@app.route("/initdb")
def initdb():
    db.create_all()
    return "Database initialized!"


# ------------------ Google OAuth ------------------
google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=["openid", "https://www.googleapis.com/auth/userinfo.profile",
           "https://www.googleapis.com/auth/userinfo.email"],
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
        flash("Your message has been sent successfully!", "success")
        return redirect("/contact")
    return render_template("contact.html")


@app.route("/signin", methods=['GET', 'POST'])
def signin():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and user.password and check_password_hash(user.password, password):
            session['user'] = {"name": user.name, "email": user.email, "picture": user.picture}
            flash("Signed in successfully!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password!", "danger")
            return redirect(url_for("signin"))

    return render_template("signin.html")


@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        try:
            new_user = User(name=name, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash("Sign up successful! Please sign in.", "success")
            return redirect(url_for('signin'))
        except:
            db.session.rollback()
            flash("Email already exists!", "danger")
            return redirect(url_for('signup'))
    return render_template("signup.html")


@app.route("/add_expense", methods=['GET', 'POST'])
def add_expense():
    if "user" not in session:
        flash("Please sign in!", "warning")
        return redirect('/signin')

    if request.method == "POST":
        date_str = request.form["date"]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

        category = request.form["category"]
        description = request.form["description"]
        amount = float(request.form["amount"])

        expense = Expense(
            user_email=session["user"]["email"],
            date=date_obj,
            category=category,
            description=description,
            amount=amount
        )
        db.session.add(expense)
        db.session.commit()

        flash("Expense added successfully!", "success")
        return redirect(url_for("add_expense"))

    return render_template("add_expense.html")


@app.route("/show_expense")
def show_expense():
    return render_template("show_expense.html")


from sqlalchemy import text

@app.route("/total_expenses")
def total_expense():
    if "user" not in session:
        flash("Please sign in!", "warning")
        return redirect(url_for("signin"))

    user_email = session["user"]["email"]
    time_period = request.args.get('time_period', 'day')

    if time_period == 'month':
        query = db.session.execute(text("""
            SELECT TO_CHAR(DATE_TRUNC('month', date), 'YYYY-MM') as time_group,
                   category, SUM(amount) as total_amount
            FROM expense
            WHERE user_email = :email
            GROUP BY DATE_TRUNC('month', date), category
            ORDER BY DATE_TRUNC('month', date) DESC
        """), {"email": user_email})

    elif time_period == 'year':
        query = db.session.execute(text("""
            SELECT EXTRACT(YEAR FROM date)::int as time_group,
                   category, SUM(amount) as total_amount
            FROM expense
            WHERE user_email = :email
            GROUP BY EXTRACT(YEAR FROM date), category
            ORDER BY EXTRACT(YEAR FROM date) DESC
        """), {"email": user_email})

    else:  # default 'day'
        query = db.session.execute(text("""
            SELECT date, category, description, amount
            FROM expense
            WHERE user_email = :email
            ORDER BY date DESC
        """), {"email": user_email})

    expenses = query.fetchall()
    total = db.session.query(db.func.sum(Expense.amount)).filter_by(user_email=user_email).scalar() or 0

    return render_template("total_expenses.html", expenses=expenses, total=total, time_period=time_period)


@app.route("/view_analysis")
def view_analysis():
    return render_template("view_analysis.html")


from sqlalchemy import text

@app.route("/api/analysis_data")
def analysis_data():
    if "user" not in session:
        return jsonify({"error": "User not authenticated"}), 401

    user_email = session["user"]["email"]
    time_period = request.args.get("time_period", "day")

    if time_period == "day":
        results = db.session.execute(text("""
            SELECT date, SUM(amount) as total_amount
            FROM expense
            WHERE user_email = :email
            GROUP BY date
            ORDER BY date ASC
        """), {"email": user_email}).fetchall()

        category_results = db.session.execute(text("""
            SELECT category, SUM(amount) as total_amount
            FROM expense
            WHERE user_email = :email
            GROUP BY category
            ORDER BY total_amount DESC
        """), {"email": user_email}).fetchall()

    elif time_period == "month":
        results = db.session.execute(text("""
            SELECT TO_CHAR(DATE_TRUNC('month', date), 'YYYY-MM') as time_group,
                   SUM(amount) as total_amount
            FROM expense
            WHERE user_email = :email
            GROUP BY DATE_TRUNC('month', date)
            ORDER BY DATE_TRUNC('month', date) ASC
        """), {"email": user_email}).fetchall()

        category_results = db.session.execute(text("""
            SELECT category, SUM(amount) as total_amount
            FROM expense
            WHERE user_email = :email
            GROUP BY category
            ORDER BY SUM(amount) DESC
        """), {"email": user_email}).fetchall()

    elif time_period == "year":
        results = db.session.execute(text("""
            SELECT EXTRACT(YEAR FROM date)::int as time_group,
                   SUM(amount) as total_amount
            FROM expense
            WHERE user_email = :email
            GROUP BY EXTRACT(YEAR FROM date)
            ORDER BY EXTRACT(YEAR FROM date) ASC
        """), {"email": user_email}).fetchall()

        category_results = db.session.execute(text("""
            SELECT category, SUM(amount) as total_amount
            FROM expense
            WHERE user_email = :email
            GROUP BY category
            ORDER BY SUM(amount) DESC
        """), {"email": user_email}).fetchall()

    # Format for Chart.js
    line_labels = [str(r[0]) for r in results]
    line_data = [float(r[1]) for r in results]
    category_labels = [r[0] for r in category_results]
    category_amounts = [float(r[1]) for r in category_results]

    return jsonify({
        "line_chart": {"labels": line_labels, "amounts": line_data},
        "category_charts": {"labels": category_labels, "amounts": category_amounts}
    })


# ------------------ Google Login Callback ------------------
@app.route("/google_login")
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch user info from Google.", "danger")
        return redirect(url_for("signin"))

    user_info = resp.json()
    email = user_info.get("email")
    name = user_info.get("name")
    picture = user_info.get("picture")

    if not email:
        flash("Google account does not have an email associated.", "danger")
        return redirect(url_for("signin"))

    try:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(name=name, email=email, picture=picture)
            db.session.add(user)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("Error saving Google user:", e)
        flash("Login failed due to a database error. Try again.", "danger")
        return redirect(url_for("signin"))

    session["user"] = {"name": name, "email": email, "picture": picture}
    flash("Signed in successfully via Google!", "success")
    return redirect(url_for("home"))


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
    with app.app_context():
        db.create_all()
    app.run(debug=True)
