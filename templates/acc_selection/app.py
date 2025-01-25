from flask import Flask, render_template, request, redirect, url_for
import shelve

app = Flask(__name__)

# Home Route
@app.route('/')
def home():
    with shelve.open('usedatadb') as db:
        data = dict(db)
        return render_template('acc_selection.html', db=data, items=data)

# Save data route
@app.route('/save', methods=['POST'])
def save():
    category = request.form.get('category')
    content = request.form.get('content')

    with shelve.open('usedatadb') as db:
        if category in db:
            db[category].append(content)
        else:
            db[category] = [content]
        return redirect(url_for('home'))

# Edit data route
@app.route('/edit/<category>/<int:item_index>', methods=['GET', 'POST'])
def edit(category, item_index):
    with shelve.open('usedatadb', writeback = True) as db:
        if request.method == 'POST':
            updated_content = request.form.get('content')
            db[category][item_index] = updated_content
            return redirect(url_for('home'))
        item = db[category][item_index]
    return render_template('edit_item.html', category=category, item=item, index=item_index)

@app.route('/delete/<category>/<int:item_index>')
def delete(category, item_index):
    with shelve.open('usedatadb', writeback= True) as db:
        if category in db and 0 <= item_index < len(db[category]):
            db[category].pop(item_index)
            if not db[category]:
                del db[category]
    return redirect(url_for('home'))

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