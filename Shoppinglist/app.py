from flask import Flask, render_template, request, redirect, url_for
import shelve

app = Flask(__name__)

DB_FILE = "shopping_list.db"

#main shopping list stuff
@app.route('/')
def index():
    with shelve.open(DB_FILE) as db:
        items = db.get("items", [])
    return render_template("index.html", items=items)


@app.route('/add', methods=['POST'])
def add_item():
    name = request.form.get("name")
    status = request.form.get("status")
    category = request.form.get("category")

    if name:
        with shelve.open(DB_FILE, writeback=True) as db:
            items = db.get("items", [])
            items.append({"name": name, "status": status, "category": category})
            db["items"] = items

    return redirect(url_for("index"))


@app.route('/delete/<int:index>')
def delete_item(index):
    with shelve.open(DB_FILE, writeback=True) as db:
        items = db.get("items", [])
        if 0 <= index < len(items):
            del items[index]
            db["items"] = items

    return redirect(url_for("index"))


@app.route('/edit/<int:index>', methods=['POST'])
def edit_item(index):
    name = request.form.get("name")
    status = request.form.get("status")
    category = request.form.get("category")

    with shelve.open(DB_FILE, writeback=True) as db:
        items = db.get("items", [])
        if 0 <= index < len(items):
            items[index] = {"name": name, "status": status, "category": category}
            db["items"] = items

    return redirect(url_for("index"))

@app.route('/calendar')
def calendar():
    return '<h1>Calendar Page (Under Construction)</h1>'

@app.route('/shopping_list')
def shopping_list():
    return '<h1>Shopping List Page (Under Construction)</h1>'

@app.route('/faq')
def faq():
    return '<h1>FAQ Page (Under Construction)</h1>'

if __name__ == '__main__':
    app.run(debug=True)
