from datetime import datetime
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, url_for
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "expenses.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_ECHO"] = True

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(200))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Expens(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    expens_count = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    expens_date = db.Column(db.String(20))

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


with app.app_context():
    db.create_all()


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            return render_template("register.html",
                                   error="Введите логин и пароль")

        user = User(username=username)
        user.set_password(password)
        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            error = "Такой пользователь уже существует"
            return render_template("register.html", error=error)

        login_user(user)
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        query = db.select(User).filter_by(username=username)
        user = db.session.scalar(query)
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))
        error = "Неверный логин или пароль"
        return render_template("login.html", error=error)
    return render_template("login.html")


@app.route("/logout", methods=["POST", "GET"])
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        raw_date = request.form.get("expens_date", "")
        raw_count = request.form.get("expens_count", "").replace(",", ".")

        if raw_date == "":
            expens_date = datetime.now()
        else:
            expens_date = datetime.strptime(raw_date, "%Y-%m-%d")

        try:
            expens_count = round(float(raw_count), 2)
        except ValueError:
            expens_count = None

        if title and expens_count is not None:
            db.session.add(Expens(title=title,
                                  expens_date=expens_date,
                                  category=category,
                                  expens_count=expens_count,
                                  user_id=current_user.id))
            db.session.commit()

        return redirect(url_for("index"))

    query = db.select(Expens).filter_by(user_id=current_user.id)
    expenses = db.session.scalars(query).all()

    return render_template("index.html", expenses=expenses)


@app.route("/delete/<int:expens_id>", methods=["POST"])
@login_required
def delete(expens_id):
    expens = db.get_or_404(Expens, expens_id)
    if expens.user_id != current_user.id:
        abort(403)
    db.session.delete(expens)
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/edit/<int:expens_id>", methods=["GET", "POST"])
@login_required
def edit(expens_id):
    expens = db.get_or_404(Expens, expens_id)
    if expens.user_id != current_user.id:
        abort(403)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        raw_date = request.form.get("expens_date", "")
        raw_count = request.form.get("expens_count", "").replace(",", ".")

        if raw_date == "":
            expens_date = datetime.now()
        else:
            expens_date = datetime.strptime(raw_date, "%Y-%m-%d")

        try:
            expens_count = round(float(raw_count), 2)
        except ValueError:
            expens_count = None

        expens.expens_count=expens_count
        expens.expens_date=expens_date
        expens.title=title
        expens.category=category
        
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("edit.html", expens=expens)


#тут пока так, надо будет реализовывать логику, пока заглушки
@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")


@app.route("/statistic")
@login_required
def statistic():
    query = db.select(Expens).filter_by(user_id=current_user.id)
    expenses = db.session.scalars(query).all()
    categorys = {}
    for expens in expenses:
        categorys[expens.category]=0
    for expens in expenses:
        categorys[expens.category]+=expens.expens_count
    return render_template("statistic.html",categorys=categorys)

if __name__ == "__main__":
    app.run(debug=True)