import datetime, shelve, requests, json, openpyxl,secrets, re, os
from flask import Flask, render_template, request, redirect, url_for, send_file, flash,session, jsonify
from io import BytesIO
from email_validator import validate_email, EmailNotValidError, EmailUndeliverableError
#from google.auth.transport import requests
from genAI import Recipes
from enum import Enum
from urllib.parse import unquote

r = Recipes()
recipeList = None
app = Flask(__name__, template_folder='templates')
app.secret_key = secrets.token_hex(16)

#ben API keys
elastic_email_api_key = '3D8744F0C7DBEAFE529B8EAAFDEB605D1534313202DA1A372B82C9B4ACE834BB711A9D24AC73A743A5C0A70A8FC338A3'
recaptcha_secret_key = '6Lc1usMqAAAAAGz-Ln0yoVCAS7f2f9azzaR8abFQ'
send_email_url = 'https://api.elasticemail.com/v2/email/send'

# validation email function
def is_valid_email(email):
    try:
        validate_email(email)
        return email
    except (EmailNotValidError,EmailUndeliverableError):
        return None
# Function to send confirmation email
def send_confirmation_email(to_email, name):
    data = {
        'apikey': elastic_email_api_key,
        'from': '242293L@mymail.nyp.edu.sg',  # Sender email (Make sure this email is verified in your Elastic Email account)
        'to': to_email,  # Recipient email
        'subject': 'Thank You for Your Feedback!',
        'bodyHtml': f"<p>Dear {name},</p><p>Thank you for your feedback!</p><p>We appreciate your time and input. Your response has been recorded, and we will consider your suggestions.</p><br><p>Best regards,<br>Your Company</p>",
        'bodyText': f"Dear {name},\n\nThank you for your feedback! We appreciate your time and input. Your response has been recorded, and we will consider your suggestions.\n\nBest regards,\nYour Company",
        'isTransactional': True  # Mark this as a transactional email
    }

    try:
        # Send POST request to Elastic Email API
        response = requests.post(send_email_url, data=data)

        # Check if the email was sent successfully
        if response.status_code == 200:
            response_data = response.json()
            if response_data['success']:
                print(f"Confirmation email sent to {to_email}.")
            else:
                print(f"Error: {response_data.get('error', 'Unknown error')}")
                print(f"Detailed error response: {response_data}")
        else:
            print(f"Failed to send email. HTTP Status code: {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

# Example usage to test. SPF error soft bounce.
send_confirmation_email('benedictwee9@gmail.com', 'Benedict Wee')
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
#function to extract meal name only
def get_meal_name(meal):
    # This regex will extract the meal name between **Meal:** and **Ingredients:**
    match = re.search(r'\*\*Meal:\*\*\s*(.*?)\r?\n', meal)
    if match:
        return match.group(1).strip()  # Return the cleaned-up recipe name
    return meal.strip()

def loadprevrecipes(key):
 recipes = request.args.get(key, None)
 recipes = json.loads(recipes)
 return recipes

@app.route('/')
def home():
    return render_template('home.html')

# zoey start
@app.route('/browse-recipes')
def loaded_recipes():
    global recipeList
    try:
        print('sent json list here??')
        recipes = loadprevrecipes('recipeslist')
        if bool(recipes):
            recipeList = recipes
            print('really changing to deleted stuff?')
        return render_template('zoey/browse-recipes.html', recipes=recipeList, r=r)
    except:
        return render_template('zoey/browse-recipes.html', recipes=r.loaded(), r=r)

@app.route('/saved-recipes')
def saved_recipes():
    with shelve.open('mealRecipes') as mr:
        saved_recipes = mr.get('recipes', [])
    return render_template('zoey/saved-recipes.html', recipes=saved_recipes, r=r)

@app.route('/meal-form/<string:which>')
def whichbutton(which):
    return render_template('zoey/meal-form.html', which=which)

@app.route('/AI-meal-creation/<string:aibtn>', methods=["POST"])
def form(aibtn):
    info = request.form
    allergies = ', '.join(info.getlist('allergies-tolerances'))
    diet_pref = ', '.join(info.getlist('dietary-preference'))
    details = [allergies, diet_pref, info['additional-notes']]
    if aibtn == 'one-meal':
        try:
            recipes = [r.one_meal_form(details)]
        except IndexError:
            return redirect(url_for('form', aibtn=aibtn))
    else:
        recipes = r.meal_plan(details)
# saving of meal into shelve db so that calendar can read it
    with shelve.open('mealRecipes', writeback=True) as mr:
        saved_recipes = mr.get('recipes', [])
        saved_recipes.append({'meal': recipes[0], 'date': datetime.datetime.now().strftime('%Y-%m-%d')})
        mr['recipes'] = saved_recipes
    return render_template('zoey/browse-recipes.html', recipes=recipes, r=r)

@app.route('/add-recipes-today')
def add_recipes_today():
    this = loadprevrecipes('this')
    recipes = request.args.get('recipeslist', [])
    print('\nadded this', this)
    with shelve.open('mealRecipes', writeback=True) as mr:
        mr['recipes'] = mr.get('recipes', []) + [{'meal': this, 'date': datetime.datetime.now().strftime('%Y-%m-%d')}]
    return redirect(url_for('loaded_recipes', recipeslist=recipes))

@app.route('/deleted-recipe/<int:index>')
def del_recipe(index):
    recipes = loadprevrecipes('recipes')
    deleted = recipes.pop(index)
    with shelve.open('mealRecipes', writeback=True) as mr:
        try:
            if bool(mr):
                delete_at = mr['recipes'].index(deleted)
                del mr['recipes'][delete_at]
            else:
                return redirect(url_for('loaded_recipes'))
        except (IndexError, KeyError, ValueError) as e:
            print(f'<h1>Delete error:</h1> <p>{e}</p>')
    encoded_recipes = json.dumps(recipes)
    return redirect(url_for('loaded_recipes', recipeslist=unquote(encoded_recipes))

@app.route('/edit_browse_recipes/<int:index>', methods=["POST", "GET"]))
def edit_browse_recipes(index):
    if request.method == 'POST':
        recipe_list = loadprevrecipes('jsonlist')
        b4update = recipe_list[index]
        recipe_list[index] = request.form['edit-meal']
        with shelve.open('mealRecipes', writeback=True) as mr:
            if 'recipes' in mr:
                try:
                    update_at = 0
                    for index, dictionary in enumerate(mr['recipes']):
                        print(dictionary, mr['recipes'])
                        if dictionary['meal'] == b4update:
                            update_at = index
                    mr['recipes'][update_at]['meal'] = request.form['edit-meal']
                    print(f"Recipe at index {index}, and database index {update_at} updated successfully.")
                except IndexError:
                    return f"Error: No recipe at index {index} in database.", 404
                except ValueError:
                    mr['recipes'] = mr.get('recipes', []) + [request.form['edit-meal']]
                    print(f"Error: No recipe {index} in database.")
        return redirect(url_for('loaded_recipes', recipeslist=json.dumps(recipe_list), r=r))
    else:
        recipe_list = loadprevrecipes('jsonlist')
        print('sending as markdown??', recipe_list)
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
                    print(f"Error: No recipe {index} in database.")
        return redirect(url_for('saved_recipes'))
    else:
        selected = request.args.get('selected')
        print('sending as markdown??', selected)
        return render_template('zoey/edit-saved-meals.html', index=index, selected=selected, r=r)
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
@app.route('/faq')
def faq():
    return render_template('ben/faq.html')


@app.route('/submit', methods=['GET', 'POST'])
def submit_feedback():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        enjoy = request.form['enjoy']
        improve = request.form['improve']
        send_confirmation_email = request.form.get('share_confirmation_email') == 'true'
        if not email or not name or not enjoy or not improve:
            flash('All fields are required.', 'error')
            # Prepare email data
            email_data = {
                'apikey': elastic_email_api_key,
                'from': '242293L@mymail.nyp.edu.sg',
                'to': email,  # Sending to user's email (assuming the form includes the user's email address)
                'subject': 'Feedback Received',
                'bodyHtml': f"<p>Thank you for your feedback, {name}!</p><p>We appreciate your comments.</p>",
                'bodyText': f"Thank you for your feedback, {name}! We appreciate your comments.",
                'isTransactional': True
            }

            # Send confirmation email to 'benedictwee9@gmail.com' only if checkbox is checked
            if send_confirmation_email:
                email_data['to'] = 'benedictwee9@gmail.com'

                response = send_confirmation_email(email_data)

                if response.status_code == 200:
                    flash('Feedback submitted successfully, and confirmation email sent!', 'success')
                else:
                    flash('There was an issue sending the confirmation email.', 'error')
            else:
                flash('Feedback submitted successfully, no confirmation email sent.', 'success')
        if not is_valid_email(email):
            session['email_error'] = True
            flash('Please enter a valid email address.', 'error')
            return redirect(url_for('feedback_form'))
        # Validate reCAPTCHA
        recaptcha_response = request.form['g-recaptcha-response']
        if not verify_recaptcha(recaptcha_response):
            flash('reCAPTCHA error failed. Please try again.','error')
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

        return redirect(url_for('feedback_form'))

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

    # Fetch saved recipes from shelve (open the shelve file only once)
    with shelve.open('mealRecipes') as mr:
        saved_recipes = mr.get('recipes', [])
        saved_recipes_names = [get_meal_name(recipe['meal']) for recipe in saved_recipes]

    # Get the selected recipe from GET parameters (this could be used for other purposes)
    selected_recipe = request.args.get('recipe')

    # Fetch weekly meals from your meal plan database
    with shelve.open('meal_plan.db') as db:
        # Use a dict comprehension for fetching weekly meals in one go
        week_meals = {day: db.get(day, None) for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}

    # Handle saving a recipe to the calendar
    if 'recipe' in request.form and 'day' in request.form:  # Ensure both recipe and day are selected
        selected_recipe = request.form['recipe']
        day = request.form['day']

        if not selected_recipe or not day:
            flash('Please select both a recipe and a day to save the meal.', 'danger')
        elif day in week_meals:
            # Save the selected recipe to the specific day in the meal plan
            week_meals[day] = {'meal': selected_recipe, 'date': current_date}

            # Update the meal plan database
            with shelve.open('meal_plan.db', writeback=True) as db:
                db[day] = week_meals[day]

            flash(f'Meal saved successfully for {day}.', 'success')
        else:
            flash('Invalid day selected.', 'danger')

    # Render the template and pass the necessary context
    return render_template(
        'ben/calendar.html',
        week_meals=week_meals,
        current_day=current_day,
        current_date=current_date,
        saved_recipes=saved_recipes_names,
        selected_recipe=selected_recipe,
        index=index,
        json_recipes =saved_recipes,
        r=r,
    )
#ben end

# trixy start
def load_products():
    return {
        1: {"name": "Organic Carrots", "price": 2.50, "image": "Carrots.jpg"},
        2: {"name": "Kale", "price": 3.20, "image": "Kale.jpg"},
        3: {"name": "Spinach", "price": 2.80, "image": "spinach.jpg"},
        4: {"name": "Bell Peppers", "price": 4.00, "image": "bell_peppers.jpg"},
        5: {"name": "Cherry Tomatoes", "price": 3.50, "image": "cherry_tomatoes.jpg"},
        6: {"name": "Zucchini", "price": 2.90, "image": "zucchini.jpg"},
        7: {"name": "Broccoli", "price": 3.00, "image": "broccoli.jpg"},
        8: {"name": "Cucumbers", "price": 2.70, "image": "cucumbers.jpg"},
        9: {"name": "Lettuce", "price": 2.40, "image": "lettuce.jpg"},
    }

@app.route('/shopping_cart')
def shopping_cart():
    products = load_products()
    with shelve.open("cart_db") as db:
        cart = db.get("cart", {})  # Load cart to check if items exist
    return render_template('trixy/shopping_cart.html', products=products, cart=cart)


@app.route('/add_to_cart/<int:product_id>', methods=['GET','POST'])
def add_to_cart(product_id):
    products = load_products()
    product = products.get(product_id)
    if product:
        with shelve.open("cart_db", writeback=True) as db:
            cart = db.get("cart", {})
            if product_id in cart:
                cart[product_id]['quantity'] += 1 #increase quantity if product is alr in cart
            else:
                cart[product_id] = {"name": product["name"], "price": product["price"], "quantity": 1} #add new item to cart if nonexistent
            db["cart"] = cart
            print(db['cart'])
    return redirect(url_for('shopping_cart'))


@app.route('/update_cart_quantity/<int:product_id>', methods=['POST'])
def update_cart_quantity(product_id):
    new_quantity = request.form.get('quantity', type=int, default=1)
    redirect_page = request.form.get('redirect_page', 'shopping_cart')  # Default to shopping page

    with shelve.open("cart_db", writeback=True) as db:
        cart = db.get("cart", {})

        if new_quantity > 0 and product_id in cart:
            cart[product_id]["quantity"] = new_quantity  # Update quantity
        elif new_quantity == 0 and product_id in cart:
            del cart[product_id]  # Remove item if quantity is set to 0

        db["cart"] = cart

    return redirect(url_for(redirect_page))


@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    with shelve.open("cart_db", writeback=True) as db:
        cart = db.get("cart", {})
        cart.pop(product_id, None)
        db["cart"] = cart

    return redirect(url_for('checkout'))

@app.route('/clear_cart')
def clear_cart():
    with shelve.open("cart_db", writeback=True) as db:
        db["cart"] = {} #reset to empty

    return redirect(url_for('checkout'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST': #if form submitted get these info from form
        name = request.form['name']
        address = request.form['address']
        postal_code = request.form['postal_code']
        email = request.form['email']
        phone = request.form['phone']

        # Calculate total price (sum of all item prices in the cart)
        with shelve.open("cart_db") as db:
            cart = db.get("cart", {})
            total_price = sum(item['price'] * item['quantity'] for item in cart.values())
            delivery_fee = 3.00
            grand_total = total_price + delivery_fee

            db["order"] = {   #save order
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
            db["cart"] = {}  # Clear cart after order

        return redirect(url_for('order_confirmation'))

    with shelve.open("cart_db") as db:
        cart = db.get("cart", {})
        total_price = sum(item['price'] * item['quantity'] for item in cart.values())
        delivery_fee = 3.00
        grand_total = total_price + delivery_fee

    return render_template('trixy/form.html', cart=cart, total_price=total_price, delivery_fee=delivery_fee, grand_total=grand_total)

@app.route('/order_confirmation')
def order_confirmation():
    with shelve.open("cart_db") as db:
        order = db.get("order", {})
        print(order)

    return render_template('trixy/response.html', order=order)

#trixy end
# disha start
#main shopping list stuff
DB_FILE = "shopping_list.db"
@app.route('/shopping-list')
def index():
    with shelve.open(DB_FILE) as db:
        items = db.get("items", [])
    return render_template("disha/shopping_list.html", items=items)


@app.route('/add-shopping-list-item', methods=['POST'])
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

    with shelve.open(DB_FILE, writeback=True) as db:
        items = db.get("items", [])
        if 0 <= index < len(items):
            items[index] = {"name": name, "status": status, "category": category}
            db["items"] = items

    return redirect(url_for("index"))
# disha end

if __name__ == '__main__':
    app.run(debug=True)