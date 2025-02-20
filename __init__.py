import re
import datetime, shelve, requests, json, openpyxl,secrets, asyncio
from flask import Flask, render_template, request, redirect, url_for, send_file, flash,session, g
from io import BytesIO
from email_validator import validate_email, EmailNotValidError, EmailUndeliverableError
from werkzeug.exceptions import BadRequestKeyError
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from Chatbot import chatbot
from Recipes import Recipes

r = Recipes()
app = Flask(__name__, template_folder='templates')
app.secret_key = secrets.token_hex(16)

#ben API keys
elastic_email_api_key = 'C6A3940726683C90239740B37D12C27A6490C80ABFFF7862FFAB432919AFFF666CEADB088A8269D4ED0350F5910FBEB8'
from_email = 'you@yourdomain.com'
recaptcha_secret_key = '6Lc1usMqAAAAAGz-Ln0yoVCAS7f2f9azzaR8abFQ'

# validation email function
def is_valid_email(email):
    try:
        validate_email(email)
        return email
    except (EmailNotValidError,EmailUndeliverableError):
        return None
# Function to verify reCAPTCHA
def verify_recaptcha(recaptcha_response):
    recaptcha_data = {
        'secret': recaptcha_secret_key,
        'response': recaptcha_response
    }
    recaptcha_verify_url = 'https://www.google.com/recaptcha/api/siteverify'
    recaptcha_response = requests.post(recaptcha_verify_url, data=recaptcha_data)
    result = recaptcha_response.json()
    return result.get('success')

@app.route('/')
def home():
    return render_template('home.html')

# zoey start
def loadprevrecipes(key):
    cached_recipes = getattr(g, '_cached_recipes', None)
    if cached_recipes is None:
        recipes = request.args.get(key, '[]')
        cached_recipes = json.loads(recipes)
        g._cached_recipes = cached_recipes
    return cached_recipes

@app.route('/browse-recipes')
def loaded_recipes():
    try:
        recipes = loadprevrecipes('recipeslist')
        with shelve.open('mealRecipes') as mr:
            save = mr.get('recipes', [])
            if bool(recipes):
                print('sent from edit to load', loadprevrecipes('recipeslist'))
                return render_template('zoey/browse-recipes.html', recipes=recipes, saved=save, r=r)
            else:
                print('this is what an empty recipeslist should look', save)
                return render_template('zoey/browse-recipes.html', recipes=asyncio.run(r.loaded()), saved=save, r=r)
    except (json.JSONDecodeError):
        with shelve.open('mealRecipes') as mr:
            save = mr.get('recipes', [])
            print('this is wahat saved recipes look', save)
            return render_template('zoey/browse-recipes.html', recipes=asyncio.run(r.loaded()), saved=save, r=r)

@app.route('/loading')
def loading():
    return render_template('zoey/recipes-loading.html')

@app.route('/meal-form')
def selected_ai_meal_plan():
    return render_template('zoey/meal-form.html', stocked=False)

@app.route('/AI-meal-creation', methods=["POST"])
def meal_form():
    info = request.form
    try:
        stocked = True if info['stock'] == 'on' else False
    except BadRequestKeyError:
        stocked = None
    allergies = ', '.join(info.getlist('allergies-tolerances'))
    diet_pref = ', '.join(info.getlist('dietary-preference'))
    details = [allergies, diet_pref, info['additional-notes']]
    with shelve.open('mealRecipes') as mr:
        print('stocked?', stocked)
        recipes = asyncio.run(r.meal_plan(details, stocked))
        jsonlist = json.dumps(recipes)
        save = mr.get('recipes', [])
        print('form?', recipes)
        return redirect(url_for('loaded_recipes', recipes=recipes, recipeslist=jsonlist, saved=save, r=r))

@app.route('/add-recipes-today')
def add_recipes_today():
    selected = request.args.get('selected', [])
    selected = json.loads(selected)
    recipes = request.args.get('recipeslist', [])
    print('\nadded dictionary', selected)
    with shelve.open('mealRecipes', writeback=True) as mr:
        selected['date'] = datetime.datetime.now().strftime('%Y-%m-%d')
        mr['recipes'] = mr.get('recipes', []) + [selected]
    return redirect(url_for('loaded_recipes', recipeslist=recipes))

@app.route('/deleted-recipe/<int:index>')
def del_recipe(index):
    recipes = loadprevrecipes('recipes')
    recipes.pop(index)
    return redirect(url_for('loaded_recipes', recipeslist=json.dumps(recipes)))

@app.route('/delete-saved-recipe/<int:index>')
def del_saved_recipe(index):
    with shelve.open('mealRecipes', writeback=True) as mr:
        del mr['recipes'][index]
        return redirect(url_for('loaded_recipes', recipeslist=request.args['recipes']))

@app.route('/edit_browse_recipes/<int:index>', methods=["POST", "GET"])
def edit_browse_recipes(index):
    if request.method == 'POST':
        recipe_list = loadprevrecipes('jsonlist')
        recipe_list[index]['meal'] = request.form['edit-meal']
        print('saving changes', recipe_list)
        return redirect(url_for('loaded_recipes', recipeslist=json.dumps(recipe_list), r=r))
    else:
        recipe_list = loadprevrecipes('jsonlist')
        print('sent to edit browse recipes', recipe_list)
        return render_template('zoey/edit-meal.html', index=index, allRecipes=recipe_list, r=r)

@app.route('/edit_saved_recipes/<int:index>', methods=["POST", "GET"])
def edit_saved_recipes(index):
    if request.method == 'POST':
        with shelve.open('mealRecipes', writeback=True) as mr:
            if 'recipes' in mr:
                try:
                    mr['recipes'][index]['meal'] = request.form['edit-meal']
                    mr['recipes'][index]['date'] = request.form['dateInput']
                    print(f"Recipe at index {index} updated successfully.")
                except IndexError:
                    return f"Error: No recipe at index {index} in database.", 404
                except ValueError:
                    print(f"Error: No recipe index {index} in database.")
        return redirect(url_for('loaded_recipes', recipeslist=request.args['jsonlist'], r=r))
    else:
        selected = request.args['selected']
        print('sending as markdown??', selected)
        jsonlist = request.args['jsonlist']
        return render_template('zoey/edit-saved-meals.html', index=index, selected=selected, jsonlist=jsonlist, r=r)
# zoey end

# ben start - misc links
@app.route('/confirm',methods=['GET','POST'])
def confirm():
    email_filter = request.args.get('email_filter','')
    # Retrieve all feedback from the database
    with shelve.open('feedback_form.db') as db:
        feedback_data = [
            {'id': key, 'name': value['name'], 'email': value['email'], 'enjoy': value['enjoy'],
             'improve': value['improve'], 'share': value['share']}
            for key, value in db.items()
        ]
    if email_filter:
        feedback_data = [feedback for feedback in feedback_data if email_filter.lower() in feedback['email'].lower()]
    return render_template('ben/confirm.html', feedback_data=feedback_data, email_filter=email_filter)

@app.route('/feedback_form')
def feedback_form():
    return render_template('ben/feedback_form.html')

replies = [{'role': 'chatbot', 'reply': 'Hi! How can I help you?'}]
@app.route('/faq', methods=['GET', 'POST'])
def faq():
 global replies
 if request.method == 'GET':
  return render_template('disha/faq.html', replies=replies, r=r)
 elif request.method == 'POST':
  print(request.form['chat'])
  chat = request.form['chat']
  bot = chatbot.bot_replies(chat)
  replies.extend([{'role': 'user','reply':chat}, bot])
  print(replies)
  return redirect(url_for('faq', replies=replies, r=r))

@app.route('/submit', methods=['GET', 'POST'])
def submit_feedback():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        enjoy = request.form['enjoy']
        improve = request.form['improve']
        send_confirmation_email = request.form.get('share_confirmation_email','false')
        session['name'] = name
        session['email'] = email
        session['enjoy'] = enjoy
        session['improve'] = improve

        if send_confirmation_email =='true':
            message = f"Hello {name},\n\nThank you for your feedback!\n\nWhat you enjoyed: {enjoy}\n\nWhat can be improved: {improve}"
        if not is_valid_email(email):
            session['email_error'] = 'Invalid email format. Please enter a valid email address.'
            return redirect(url_for('feedback_form'))
        session.pop('email_error',None)
        flash('Feedback submitted successfully! Thank you!','success')
        # Validate reCAPTCHA
        recaptcha_response = request.form['g-recaptcha-response']
        if not verify_recaptcha(recaptcha_response):
            flash('reCAPTCHA failed. Please try again.','error')
            session['name'] = name
            session['email'] = email
            session['enjoy'] = enjoy
            session['improve'] = improve
            session['share'] = send_confirmation_email
            return redirect(url_for('feedback_form'))

        # Save feedback to the database after passing all validations
        with shelve.open('feedback_form.db') as db:
            feedback_id = str(max([int(key) for key in db.keys()], default=0) + 1)
            feedback_data = {
                'name': name,
                'email': email,
                'enjoy': enjoy,
                'improve': improve,
                'share': send_confirmation_email
            }
            db[feedback_id] = feedback_data
        print(f'feedback: {feedback_data}')

    # In case of a non-POST request, redirect to the feedback form
    return redirect(url_for('feedback_form'))
@app.route('/delete/<int:feedback_id>', methods=['POST'])
def delete_feedback(feedback_id):
    with shelve.open('feedback_form.db') as db:
        if str(feedback_id) in db:
            del db[str(feedback_id)]
    return redirect(url_for('confirm'))  # Redirect to the confirm page after deletion

@app.route('/edit/<int:feedback_id>', methods=['GET', 'POST'])
def edit_feedback(feedback_id):
    with shelve.open('feedback_form.db') as db:
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

        with shelve.open('feedback_form.db') as db:
            db[feedback_key] = {'name': name, 'email': email, 'enjoy': enjoy, 'improve': improve, 'share': share}
    flash('Feedback has been updated.','success')
    return render_template('ben/edit_feedback.html', feedback=feedback, feedback_id=feedback_id)


@app.route('/export', methods=['GET'])
def export_feedback():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Feedback"
    ws.append(["ID", "Name", "Email", "Enjoy", "Improve", "Share"])

    with shelve.open('feedback_form.db') as db:
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
    # Fetch saved recipes from shelve
    with shelve.open('mealRecipes') as mr:
        saved_recipes = mr.get('recipes', [])
        saved_recipes_names = [recipe['mealname'] for recipe in saved_recipes]

        # Get the selected recipe from GET parameters (this could be used for other purposes)
        selected_recipe = request.args.get('recipe')

        # Fetch weekly meals from your meal plan database
        with shelve.open('meal_plan.db') as db:
            week_meals = {str(day): db.get(day, None) for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}

            # Handle saving a recipe to the calendar
            if 'recipe' in request.form:  # Checking if a recipe is selected
                selected_recipe = request.form['recipe']  # The selected recipe
                day = request.form['day']  # The day the user wants to save the recipe to

                if day in week_meals:
                    # Save the selected recipe to the specific day in the meal plan
                    week_meals[day] = {'meal': selected_recipe, 'date': current_date}

                    # Update the meal plan database
                    with shelve.open('meal_plan.db', writeback=True) as db:
                        db[day] = week_meals[day]

            # Handle deletion of a meal from the calendar
            elif 'delete' in request.form and request.form['delete'] == 'true':
                day = request.form['day']
                if day in week_meals:
                    week_meals[day] = None
                    with shelve.open('meal_plan.db') as db:
                        del db[day]

            # Render the template and pass the necessary context
            return render_template(
                'ben/calendar.html',
                week_meals=week_meals,
                current_day=current_day,
                current_date=current_date,
                saved_recipes=saved_recipes_names,
                selected_recipe=selected_recipe,
            )
#ben end

# trixy start
def load_products(category=None):
    products = {
        'Vegetables':{

            1: {"name": "Organic Carrots", "price": 2.50, "image": "Carrots.jpg", "category": "Vegetables"},
            2: {"name": "Kale", "price": 3.20, "image": "Kale.jpg", "category": "Vegetables"},
            3: {"name": "Spinach", "price": 2.80, "image": "spinach.jpg", "category": "Vegetables"},
            4: {"name": "Bell Peppers", "price": 4.00, "image": "bell_peppers.jpg", "category": "Vegetables"},
            5: {"name": "Cherry Tomatoes", "price": 3.50, "image": "cherry_tomatoes.jpg", "category": "Vegetables"},
            6: {"name": "Zucchini", "price": 2.90, "image": "zucchini.jpg", "category": "Vegetables"},
            7: {"name": "Broccoli", "price": 3.00, "image": "broccoli.jpg", "category": "Vegetables"},
            8: {"name": "Cucumbers", "price": 2.70, "image": "cucumbers.jpg", "category": "Vegetables"},
            9: {"name": "Lettuce", "price": 2.40, "image": "lettuce.jpg", "category": "Vegetables"},
        },
        'Fruits': {
            1: {"name": "Bananas", "price": 2.99, "image": "bananas.png", "category": "Fruits"},
            2: {"name": "Blueberries", "price": 4.99, "image": "blueberries.jpg", "category": "Fruits"},
            3: {"name": "Apples", "price": 3.49, "image": "apples.jpg", "category": "Fruits"},
            4: {"name": "Mangoes", "price": 5.99, "image": "mangoes.jpg", "category": "Fruits"},
            5: {"name": "Strawberries", "price": 6.99, "image": "strawberries.jpg", "category": "Fruits"},
            6: {"name": "Avocados", "price": 3.29, "image": "avocados.jpg", "category": "Fruits"},
            7: {"name": "Oranges", "price": 4.29, "image": "oranges.jpg", "category": "Fruits"},
            8: {"name": "Grapes", "price": 7.99, "image": "grapes.jpg", "category": "Fruits"},
            9: {"name": "Pineapple", "price": 5.49, "image": "pineapples.jpg", "category": "Fruits"},
        },
        'Meat': {
            1: {"name": "Chicken Breast", "price": 2.99, "image": "chicken_breast.jpg", "category": "Meat"},
            2: {"name": "Ground Beef", "price": 4.99, "image": "ground_beef.jpg", "category": "Meat"},
            3: {"name": "Pork Tenderloin", "price": 3.49, "image": "pork_tenderloin.jpg", "category": "Meat"},
            4: {"name": "Ground Turkey", "price": 5.99, "image": "ground_turkey.jpg", "category": "Meat"},
            5: {"name": "Salmon", "price": 6.99, "image": "salmon.jpg", "category": "Meat"},
            6: {"name": "Lamb Chops", "price": 3.29, "image": "lamb_chops.jpg", "category": "Meat"},
            7: {"name": "Beef Steak", "price": 4.29, "image": "beef_steak.jpg", "category": "Meat"},
            8: {"name": "Duck Breast", "price": 7.99, "image": "duck_breast.jpg", "category": "Meat"},
            9: {"name": "Chicken Thighs", "price": 5.49, "image": "chicken_thighs.jpg", "category": "Meat"},
        },
    'Carbohydrates': {

            1: {"name": "Sweet Potatoes", "price": 3.49, "image": "sweet_potatoes.jpg", "category": "Carbohydrates"},
            2: {"name": "Brown Rice", "price": 4.29, "image": "brown_rice.jpg", "category": "Carbohydrates"},
            3: {"name": "Bread", "price": 3.99, "image": "bread.jpg", "category": "Carbohydrates"},
            4: {"name": "Oats", "price": 3.79, "image": "oats.jpg", "category": "Carbohydrates"},
            5: {"name": "Cornmeal", "price": 2.99, "image": "cornmeal.jpg", "category": "Carbohydrates"},
            6: {"name": "Potatoes", "price": 4.99, "image": "potatoes.jpg", "category": "Carbohydrates"},
            7: {"name": "Spaghetti", "price": 2.99, "image": "spaghetti.jpg", "category": "Carbohydrates"},
            8: {"name": "Polenta", "price": 3.49, "image": "polenta.jpg", "category": "Carbohydrates"},
            9: {"name": "Couscous", "price": 4.49, "image": "couscous.jpg", "category": "Carbohydrates"},
        },
    'Pantry':{
            1: {"name": "Olive Oil", "price": 7.99, "image": "olive_oil.jpg", "category": "Pantry"},
            2: {"name": "Quinoa", "price": 5.49, "image": "quinoa.jpg", "category": "Pantry"},
            3: {"name": "Coconut Flour", "price": 4.99, "image": "coconut_flour.jpg", "category": "Pantry"},
            4: {"name": "Canned Tomatoes", "price": 2.49, "image": "canned_tomatoes.jpg", "category": "Pantry"},
            5: {"name": "Peanut Butter", "price": 4.89, "image": "peanut_butter.jpg", "category": "Pantry"},
            6: {"name": "Rolled Oats", "price": 3.79, "image": "rolled_oats.jpg", "category": "Pantry"},
            7: {"name": "Black Beans", "price": 1.99, "image": "black_beans.jpg", "category": "Pantry"},
            8: {"name": "Cider Vinegar", "price": 3.49, "image": "apple_cider.jpg", "category": "Pantry"},
            9: {"name": "Honey", "price": 5.29, "image": "honey.jpg", "category": "Pantry"},
        }
    }
    if category:
        return products.get(category, {})
    else:
        # Return all products if no category is specified
        all_products = {}
        for cat in products:
            all_products.update(products[cat])
        return all_products

@app.route('/shopping-cart')
def shopping_cart():
    # Load all products
    products = load_products()  # No category argument means load all products

    # Load cart from Shelve
    with shelve.open("cart_db") as db:
        cart = db.get("cart", {})

    return render_template('trixy/shopping_cart.html', cart=cart, products=products)

@app.route('/category/<category>')
def category(category):
    if category not in ['Vegetables', 'Fruits', 'Meat', 'Carbohydrates', 'Pantry']:
        abort(404)  # Return a 404 error for invalid categories

    products = load_products(category)
    with shelve.open("cart_db") as db:
        cart = db.get("cart", {})

    return render_template('trixy/shopping_cart.html', category=category, products=products, cart=cart)
@app.route('/add_to_cart/<category>/<int:product_id>', methods=['POST'])
def add_to_cart(category, product_id):
    products = load_products(category)
    product = products.get(product_id)
    if product:
        with shelve.open("cart_db", writeback=True) as db:
            cart = db.get("cart", {})
            if product_id in cart:
                cart[product_id]['quantity'] += 1
            else:
                cart[product_id] = {"name": product["name"], "price": product["price"], "quantity": 1, "category": product["category"]}
            db["cart"] = cart
    return redirect(url_for('category', category=category))

@app.route('/update_cart_quantity/<int:product_id>', methods=['POST'])
def update_cart_quantity(product_id):
    if request.method != 'POST':
        abort(405)
    new_quantity = request.form.get('quantity', type=int, default=1)
    with shelve.open("cart_db", writeback=True) as db:
        cart = db.get("cart", {})
        if product_id in cart:
            if new_quantity > 0:
                cart[product_id]["quantity"] = new_quantity
            else:
                del cart[product_id]
        db["cart"] = cart
    return redirect(request.referrer or url_for('shopping_cart'))

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    with shelve.open("cart_db", writeback=True) as db:
        cart = db.get("cart", {})
        cart.pop(product_id, None)
        db["cart"] = cart

    # Redirect to the previous page (either shopping cart or category)
    referrer = request.referrer  # Get the URL of the previous page
    if referrer and 'category' in referrer:
        return redirect(referrer)  # Redirect back to the category page
    else:
        return redirect(url_for('checkout'))


@app.route('/clear_cart')
def clear_cart():
    with shelve.open("cart_db", writeback=True) as db:
        db["cart"] = {}
    return redirect(url_for('checkout'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    today = datetime.datetime.today()
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        postal_code = request.form['postal_code']
        email = request.form['email']
        phone = request.form['phone']

        with shelve.open("cart_db") as db:
            cart = db.get("cart", {})
            total_price = sum(item['price'] * item['quantity'] for item in cart.values())
            delivery_fee = 3.00
            grand_total = total_price + delivery_fee

            db["order"] = {
                "name": name,
                "address": address,
                "postal_code": postal_code,
                "email": email,
                "phone": phone,
                "cart": cart,
                "total_price": total_price,
                "delivery_fee": delivery_fee,
                "grand_total": grand_total
            }
            db["cart"] = {}

        return redirect(url_for('order_confirmation'))

    with shelve.open("cart_db") as db:
        cart = db.get("cart", {})
        total_price = sum(item['price'] * item['quantity'] for item in cart.values())
        delivery_fee = 3.00
        grand_total = total_price + delivery_fee

    return render_template('trixy/form.html', cart=cart, total_price=total_price, delivery_fee=delivery_fee, grand_total=grand_total, today=today)

@app.route('/order_confirmation')
def order_confirmation():
    with shelve.open("cart_db") as db:
        order = db.get("order", {})

    if not order:
        return redirect(url_for('shopping_cart'))  # Redirect if no order exists

    # Extract values safely
    cart = order.get("cart", {})
    total_price = order.get("total_price", 0)
    delivery_fee = order.get("delivery_fee", 3.00)
    grand_total = order.get("grand_total", total_price + delivery_fee)

    return render_template('trixy/response.html', order=order, cart=cart, total_price=total_price, delivery_fee=delivery_fee, grand_total=grand_total)
#trixy end
# disha start
DB_FILE = "shopping_list.db"
@app.route('/ingredients-list')
def index():
    with shelve.open(DB_FILE) as db:
        items = db.get("items", [])
    return render_template("disha/shopping_list.html", items=items)


@app.route("/add-shopping-list-item", methods=["POST"])
def add_item():
    name = request.form.get("name")
    quantity = request.form.get("quantity")  # Get quantity
    status = request.form.get("status")
    category = request.form.get("category")

    if name and quantity and status and category:
        with shelve.open("shopping_list.db") as db:
            if "items" not in db:
                db["items"] = []

            items = db["items"]
            items.append({
                "name": name,
                "quantity": int(quantity),  # Ensure quantity is an integer
                "status": status,
                "category": category
            })
            db["items"] = items  # Save back to shelve

    return redirect(url_for("index"))


@app.route('/delete-shopping-list-item/<int:index>')
def delete_item(index):
    with shelve.open(DB_FILE, writeback=True) as db:
        items = db.get("items", [])
        if 0 <= index < len(items):
            del items[index]
            db["items"] = items

    return redirect(url_for("index"))

@app.route('/edit-shopping-list-item/<int:index>', methods=['POST'])
def edit_item(index):
    name = request.form.get("name")
    status = request.form.get("status")
    category = request.form.get("category")
    quantity = request.form.get("quantity")  # Get quantity

    with shelve.open(DB_FILE, writeback=True) as db:
        items = db.get("items", [])
        if 0 <= index < len(items):
            items[index] = {"name": name, "status": status, "category": category, "quantity" : quantity}
            db["items"] = items

    return redirect(url_for("index"))

#main shopping list stuff
def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "role" not in session or session["role"] != "super_admin":
            flash("Unauthorized access!!", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated_function


# Setting up default admin users in the shelve database
with shelve.open("users") as shelve_db:
    if "super_admin" not in shelve_db:
        shelve_db["super_admin"] = {
            "password": generate_password_hash("Super_admin123"),
            "role": "super_admin"
        }
    if "admin" not in shelve_db:
        shelve_db["admin"] = {
            "password": generate_password_hash("admin123"),
            "role": "admin"
        }

@app.route('/<admin>', methods=['POST','GET'])
def admin(admin):
 if admin == 'admin':
  if request.method == 'POST':
   username = request.form['username']
   password = request.form['password']

   stored_password_hash = None
   role = None

   with shelve.open("users") as db:
    if username in db:
     user_data = db[username]
     stored_password_hash = user_data.get("password")
     role = user_data.get("role")

   if stored_password_hash and check_password_hash(stored_password_hash, password):
    session['username'] = username
    session['role'] = role
    flash("Login successful!", 'success')
    return redirect(url_for('dashboard'))

   flash('Invalid username or password!', 'danger')
   return render_template('disha/login.html', title=admin)
 else:
  return 'ERROR 404. Unauthorized personnel will have restricted access.'


@app.route('/dashboard')
def dashboard():
    return render_template('disha/dashboard.html', role=session.get("role"))


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    with shelve.open("users") as db:
        admins = {key: db[key] for key in db if db[key]["role"] == "admin"}  # Get all admins

        if request.method == 'POST':
            new_username = request.form["new_username"]
            new_password = request.form["new_password"]

            # ✅ Ensure username is unique
            if new_username in db:
                flash("Username already exists!", "danger")
            else:
                db[new_username] = {
                    "password": generate_password_hash(new_password),
                    "role": "admin"
                }
                flash(f"Admin user '{new_username}' created successfully!", "success")
            return redirect(url_for("profile"))  # Refresh page

    return render_template("disha/profile.html", admins=admins)


@app.route('/delete_admin/<username>', methods=['POST'])
@super_admin_required
def delete_admin(username):
    with shelve.open("users") as db:
        if username in db:
            del db[username]
            flash(f"Admin '{username}' has been deleted.", "success")
        else:
            flash("Admin not found!", "danger")

    return redirect(url_for("profile"))
# disha end

if __name__ == '__main__':
    app.run(debug=True)