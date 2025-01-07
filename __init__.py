from flask import Flask, request, redirect, url_for, render_template
# from app_blueprint import blueprint # app.register_blueprint(blueprint)
from chatgp import Recipes

r = Recipes()
recipeList = None
app = Flask(__name__, template_folder='templates')
# will be figuring out how to add my ai sht in a more cleaner n easy to read manner - zoey

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/calendar')
def cale():
    return render_template('calendar.html')


# zoey start
@app.route('/browse-recipes')
def loaded_recipes():
 global recipeList
 recipeList = r.loaded()
 return render_template('forproj/browse-recipes.html', recipes = recipeList)

@app.route('/meal-form/<string:which>')
def whichbutton(which):
 # ASSUMING THE ONLY WAY TO GET TO THIS FUNCTION IS BY CLICKING EITHER BTN
 print(which)
 return render_template('forproj/meal-form.html', which = which)

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
 return render_template('forproj/browse-recipes.html', recipes = recipeList)
# zoey end


if __name__ == '__main__':
    app.run(debug=True)