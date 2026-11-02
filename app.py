from datetime import datetime 

from pathlib import Path

from sqlalchemy import func 
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "expenses.db"

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_ECHO"] = True

db = SQLAlchemy(app)

class Expens(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    expens_count = db.Column(db.Float, nullable=False)
    
    expens_date = db.Column(db.String(20))

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        expens_date = datetime.strptime(request.form["expens_date"], "%Y-%m-%d")
        expens_count = round(float(request.form["expens_count"]), 2)
        #print(expens_count)

        if title:
            
            db.session.add(Expens(title=title, 
                            expens_date=expens_date, category=category, expens_count=expens_count))
            db.session.commit()

        #return redirect(url_for("index"))

    query = db.select(Expens)

    expenses = db.session.scalars(query).all()

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

    app.run(debug=True)