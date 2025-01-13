import shelve
import datetime
from meal_data import meals
from flask import Flask, request, redirect, url_for, render_template
# from app_blueprint import blueprint # app.register_blueprint(blueprint)
from genAI import Recipes

r = Recipes()
recipeList = None
app = Flask(__name__, template_folder='templates')
# will be figuring out how to add my AI sht in a more cleaner n easy to read manner - zoey

#ben global retrieve db database bc i lazyy
def get_db(db_name):
    return shelve.open(db_name, writeback= True)

@app.route('/')
def home():
    return render_template('index.html')

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

# ben start 
    # various misc links
@app.route('/faq')
def faq():
    return render_template('/ben/faq.html')

@app.route('/feedback')
def feedback():
    return render_template('/ben/feedback.html')

@app.route('/shopping-list')
def shopping_list():
    return render_template('/ben/shopping-list.html')

@app.route('/submit', methods=['POST'])
def submit_feedback():
    if request.method == ['POST']:
        name = request.form.get('name')
        email = request.form.get('email')
        feedback = request.form.get('feedback')
        enjoy = request.form.get('enjoy')
        improvement = request.form.get('improvement')
        recommend = request.form.get('recommend')
        suggestions = request.form.get('suggestions')
        ease_of_use = request.form.get('ease_of_use')
        if not name or not email or not feedback:
                return 'Name, email, and feedback are required!', 400
        # generate feedback number + entry for removal later in feedback_entries.html
        with get_db('feedback.db') as db:
            feedback_id = str(len(db) + 1)
            db[feedback_id] = {
                'name': name,
                'email': email,
                'feedback': feedback,
                'enjoy': enjoy,
                'improvement': improvement,
                'recommend': recommend,
                'suggestions': suggestions,
                'ease_of_use': ease_of_use
            }
            return f"Thank you for your feedback."
@app.route('/view_feedback')
def view_feedback():
   with get_db('feedback.db') as db:
      feedback = db.items()
      return render_template('feedback_entries.html', feedback=feedback)

@app.route('/delete_feedback/<feedback_id>', methods=['POST'])
def delete_feedback(feedback_id):
    with get_db('feedback.db') as db:
        if feedback_id in db:
            del db[feedback_id]
    return redirect(url_for('view_feedbacks'))

@app.route('/set_allergies', methods=['POST'])
def set_allergies():
    allergies = request.form.getlist('allergies')
    with get_db('user_data.db') as db:
        db['allergies'] = allergies
    return redirect(url_for('meal_plan'))

# Updates & refreshes meal according to user allergies
@app.route('/meal_plan', methods=['GET', 'POST'])
def meal_plan():
    with get_db('user_data.db') as db:  # Connection to user database
        allergies = db.get('allergies', [])  # Load allergies that user has with nil as default

    with get_db('meals.db') as db:
        if request.method == 'POST':
            meal = request.form['meal']
            allergens = request.form.getlist('allergies')
            db[meal] = allergens  # Updates meal name & list of allergens saves it

        meals = dict(db)

    # Create a separate dictionary where meals with user allergens are removed. Only meals that user is not allergic to
    filtered_meals = {
        meal: allergens for meal, allergens in meals.items()
        if not any(allergen in allergies for allergen in allergens)
    }  # For allergen check, if allergen is in list, remove it. Otherwise, put it in the dictionary

    return render_template('meal.html', meals=filtered_meals)

@app.route('/calendar', methods=['GET', 'POST'])
def calendar():
    today = datetime.datetime.now()
    # provide meal every day of the month 

    return render_template('/ben/calendar.html')

# on click on day, provide more nutirional information abt meal. not working however
@app.route('/meal/<day>', methods=['GET'])
def get_meal_details():
    today = datetime.datetime.now()
    meal = meals.get(today,'Pasta')

    with get_db('meal.db') as db:
        db['today_meal'] = meal

    return render_template('meal_data.py')
# ben end


if __name__ == '__main__':
    app.run(debug=True)