# from app_blueprint import blueprint # app.register_blueprint(blueprint)
import openpyxl
from google.auth.transport import requests

from genAI import Recipes
import datetime
import shelve
import requests
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
from io import BytesIO

r = Recipes()
recipeList = None
app = Flask(__name__, template_folder='templates')
# will be figuring out how to add my AI sht in a more cleaner n easy to read manner - zoey

#ben global retrieve db + API keys for storage
def get_db(db_name):
    return shelve.open(db_name, writeback= True)
spoonacular_api_key = 'f2b5dac1a58f4de4bd5eb5838894e3c9' # food nutri information
spoonacular_url = 'https://api.spoonacular.com/food/ingredients/{}/information'
email_verify_api_key = 'test_93f79f744aa6b020f21e'
recaptcha_secret_key = '6LeIxAcTAAAAAMt8sT0oFAghcH9uQfK8rIglxaYw'

@app.route('/')
def home():
    return render_template('home.html')

# zoey start
@app.route('/browse-recipes')
def loaded_recipes():
 global recipeList
 recipeList = r.loaded()
 return render_template('browserecipes/browse-recipes.html', recipes = recipeList)

@app.route('/meal-form/<string:which>')
def whichbutton(which):
 # ASSUMING THE ONLY WAY TO GET TO THIS FUNCTION IS BY CLICKING EITHER BTN
 print(which)
 return render_template('browserecipes/meal-form.html', which = which)

# after they fill out the form, their button will be dependent on True False stuff
@app.route('/create_AI_meal/<string:aibtn>', methods=["POST"])
def form(aibtn):

 global recipeList
 info = request.form
 allergies = ', '.join(info.getlist('allergies-tolerances'))
 diet_pref = ', '.join(info.getlist('dietary-preference'))
 print('just submitted form', info, [allergies, diet_pref, info['additional-notes']])
 details = [allergies, diet_pref, info['additional-notes']]
 # userinput = r.user_form_input([allergies, diet_pref, info['additional-notes']])
 # print(userinput)
 print(aibtn)

 # https://stackoverflow.com/questions/1679384/converting-dictionary-to-list
 if aibtn == 'one-meal':
  recipeList = [r.one_meal_form(details)]
 else:
  recipeList = r.meal_plan(details)
 return render_template('browserecipes/browse-recipes.html', recipes = recipeList)
# zoey end

# ben start - misc links
@app.route('/confirm')
def confirm():
    return render_template('ben/confirm.html')
@app.route('/feedback_form')
def feedback_form():
    return render_template('ben/feedback_form.html')
@app.route('/faq')
def faq():
    return render_template('ben/faq.html')
@app.route('/nutri_info')
def nutri_info():
    return render_template('ben/nutri_info.html')

@app.route('/submit', methods=['GET', 'POST'])
def submit_feedback():
    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        enjoy = request.form['enjoy']
        improve = request.form['improve']
        share = 'share' in request.form

        recaptcha_response = request.form['g-recaptcha-response']
        recaptcha_data = {
            'secret': recaptcha_secret_key,
            'response': recaptcha_response
        }
        recaptcha_verify_url = 'https://www.google.com/recaptcha/api/siteverify'
        recaptcha_response = requests.post(recaptcha_verify_url, data=recaptcha_data)
        result = recaptcha_response.json()

        if result.get('success'):
            with get_db('feedback_form.db') as db:
                feedback_id = str(max([int(key) for key in db.keys()], default=0) + 1)
                feedback_data = {'name': name, 'email': email, 'enjoy': enjoy, 'improve': improve, 'share': share}
                db[feedback_id] = feedback_data

        return redirect(url_for('confirm'))

@app.route('/retrieve')
def retrieve():
    email_filter = request.args.get('email_filter', '')
    print(f'Email Filter: {email_filter}') # debug statement remind me to take out

    with get_db('feedback_form.db') as db:
        filtered_feedback = [
            {'id': key, 'name': feedback['name'], 'email': feedback['email'], 'enjoy': feedback['enjoy'],
             'improve': feedback['improve'], 'share': feedback['share']}
            for key, feedback in db.items()
            if email_filter.lower() in feedback['email'].lower()
        ]
        return jsonify(filtered_feedback)


@app.route('/delete/<int:feedback_id>', methods=['POST'])
def delete_feedback(feedback_id):
    with get_db('feedback_form.db') as db:
        if str(feedback_id) in db:
            del db[str(feedback_id)]
    return redirect(url_for('feedback_form'))


@app.route('/edit/<int:feedback_id>', methods=['GET', 'POST'])
def edit_feedback(feedback_id):
    with get_db('feedback_form.db') as db:
        feedback_key = str(feedback_id)
        if feedback_key not in db:
            return redirect(url_for('feedback_form'))

        feedback = db[feedback_key]

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        enjoy = request.form['enjoy']
        improve = request.form['improve']
        share = 'share' in request.form

        with get_db('feedback_form.db') as db:
            db[feedback_key] = {'name': name, 'email': email, 'enjoy': enjoy, 'improve': improve, 'share': share}

        return redirect(url_for('feedback_form'))

    return render_template('ben/edit_feedback.html', feedback=feedback, feedback_id=feedback_id)


@app.route('/export', methods=['GET'])
def export_feedback():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Feedback"
    ws.append(["ID", "Name", "Email", "Enjoy", "Improve", "Share"])

    with get_db('feedback_form.db') as db:
        for feedback_id, feedback in db.items():
            ws.append([feedback_id, feedback['name'], feedback['email'], feedback['enjoy'], feedback['improve'],
                       feedback['share']])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(output, as_attachment=True, download_name="feedback.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Calendar code
@app.route('/calendar', methods=['GET', 'POST'])
def calendar():
    today = datetime.datetime.now()
    current_date = today.strftime('%Y-%m-%d')
    current_day = today.strftime('%A')

    with get_db('meal_plan.db') as db:
        week_meals = {str(day): db.get(day, None) for day in
                      ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}

    if 'meal' in request.form:
        meal_name = request.form['meal']
        day = request.form['day']
        if day in week_meals:
            week_meals[day] = {'name': meal_name, 'date': current_date}
            with shelve.open('meal_plan.db') as db:
                db[day] = week_meals[day]

    elif 'delete' in request.form and request.form['delete'] == 'true':
        day = request.form['day']
        if day in week_meals:
            week_meals[day] = None
            with shelve.open('meal_plan.db') as db:
                del db[str(day)]

    return render_template('ben/calendar.html', week_meals=week_meals, current_day=current_day,current_date=current_date)

#third party stuff
@app.route('/get_nutrition/<food_name>', methods=['GET'])
def get_nutrition(food_name):
    food_name = food_name.replace(" ", "%20")  # replace space for error prevention

    # API request to search for the ingredient
    ingredient_url = f"https://api.spoonacular.com/food/ingredients/search"
    params = {
        'apiKey': spoonacular_api_key,
        'query': food_name,
        'number': 1
    }

    response = requests.get(ingredient_url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data['results']:
            ingredient = data['results'][0]
            ingredient_id = ingredient['id']

            # calls for nutrionial information by right
            nutrition_url = spoonacular_url.format(ingredient_id)
            nutrition_response = requests.get(nutrition_url, params={'apiKey': spoonacular_api_key})

            if nutrition_response.status_code == 200:
                nutrition_data = nutrition_response.json()
                nutrition_info = {
                    'name': ingredient.get('name', 'N/A'),
                    'image': ingredient.get('image', 'N/A'),
                    'possibleUnits': ingredient.get('possibleUnits', 'N/A'),
                    'consistency': ingredient.get('consistency', 'N/A'),
                    'aisle': ingredient.get('aisle', 'N/A'),
                    'categoryPath': ingredient.get('categoryPath', 'N/A')
                }

                return jsonify(nutrition_info)
            else:
                return jsonify({'error': 'Could not retrieve nutrition data for this ingredient'}), 400
        else:
            return jsonify({'error': 'Ingredient not found'}), 404
    else:
        return jsonify({'error': 'Failed to search for the ingredient'}), 400

# third party verify email API not working.
@app.route('/verify_email', methods=['POST'])
def verify_email():
    email = request.form.get('email')

    if email:
        url = f"https://emailverifyapi.com/api/v3/lookups/json?apiKey={email_verify_api_key}&email={email}"
        response = requests.get(url)
        result = response.json()

        if result.get('status') == 'success' and result.get('is_valid'):
            return jsonify({"message": "Email is valid!"}), 200
        else:
            return jsonify({"message": "Invalid email address."}), 400
    return jsonify({"message": "No email provided."}), 400


if __name__ == '__main__':
    app.run(debug=True)