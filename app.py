from datetime import datetime 

from pathlib import Path

from sqlalchemy import func 
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from flask_login import LoginManager, UserMixin
from flask_login import login_user, logout_user
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

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


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = User(username=request.form["username"])
        user.set_password(request.form["password"])
        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            error = "Такой пользователь уже существует"
            return render_template("register.html", error=error)
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
        raw_date = request.form["expens_date"]

        #потом сделать по другому надо, это пока чисто заглушка
        if raw_date == "": 
            expens_date = datetime.now() 
        else:
            expens_date = datetime.strptime(raw_date, "%Y-%m-%d")
            
        expens_count = round(float(request.form["expens_count"]), 2)
        #print(expens_count)

        if title:
            
            db.session.add(Expens(title=title, 
                            expens_date=expens_date, category=category, expens_count=expens_count, user_id=current_user.id))
            db.session.commit()

            #return redirect(url_for("index"))

    query = db.select(Expens)

    expenses = db.session.scalars(query.filter_by(
        user_id=current_user.id)).all()

    return render_template("index.html", expenses=expenses)


@app.route("/delete/<int:expens_id>", methods=["POST"])
def delete(expens_id):
    expens = db.get_or_404(Expens, expens_id)
    db.session.delete(expens)
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/edit/<int:expens_id>", methods=["GET", "POST"])
def edit(expens_id):
    expens = db.get_or_404(Expens, expens_id)
    if request.method == "POST":
        expens.title = request.form["title"]
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("edit.html", task=expens)



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    app.run(debug=True)

