import google.generativeai as genai
import markdown, json, shelve, re, requests, asyncio, aiohttp


genai.configure(api_key="AIzaSyArgfuunvoAXWkYrCrhexEFFE-9cAC5D4I")
model = genai.GenerativeModel('gemini-1.5-flash')


class Images:
 def __init__(self):
  self.searchAPI = 'b276cd4d18f1e4e40'
  self.ZOEY_APIKEY = 'AIzaSyAeAwZr8nuyspgq-R0m3oznPPJSn0g6ypI'

 # def fetch_meal_image_urls(self, query, num_results=1):
 #  print('quering', query)
 #  url = "https://www.googleapis.com/customsearch/v1"
 #  params = {
 #   'q': query,
 #   'key': self.ZOEY_APIKEY,
 #   'cx': self.searchAPI,
 #   'searchType': 'image',
 #   'num': num_results,  # The number of results to fetch (max 10 per query)
 #  }
 #  response = requests.get(url, params=params)
 #  data = response.json()
 #  # print('img data u want ', data)
 #  if 'items' in data and data['items']:
 #   image_url = data['items'][0]['link']
 #   return image_url
 #  else:
 #   print("No image found.")
 #   return 'noimage.png'

 async def fetch_meal_image_urls(self, query, num_results=1):
  print('querying', query)
  url = "https://www.googleapis.com/customsearch/v1"
  params = {
   'q': query,
   'key': self.ZOEY_APIKEY,
   'cx': self.searchAPI,
   'searchType': 'image',
   'num': num_results,  # The number of results to fetch (max 10 per query)
  }

  # Perform the async HTTP request
  async with aiohttp.ClientSession() as session:
   async with session.get(url, params=params) as response:
    data = await response.json()

    if 'items' in data and data['items']:
     image_url = data['items'][0]['link']
     return image_url
    else:
     print("No image found.")
     return 'noimage.png'


# Async method to fetch images for multiple meal names
 async def fetch_images_for_meals(self, meal_names):
  tasks = [self.fetch_meal_image_urls(meal) for meal in meal_names]
  return await asyncio.gather(*tasks)

 def get_listofmealnames(self, recipes_list):
  mealnames = recipes_list.split(',')
  # print('mealname???', mealnames)
  return mealnames

 def identify_img(self, img_address):
  if isinstance(img_address, str):
   prompt = """identify this and produce your results in this dictionary: 
   {"name": "<name of the picture>", "category": "<fruit/vegetable/meat>"}\n""" + img_address
   model.generate_content(prompt)
   return {"name": 'pic', 'category': 'idk', 'imgurl': img_address}
  else:
   print('please ensure img address is a string')


i = Images()

# so when we click on a meal, it should show the markdown text instead of the html or text content
async def return_markdown(text):
 new_text = text.split('End of meal.')
 print('hopefully is markdwon',new_text)
 new_text.pop(-1)
 return new_text

def accessing_shoppinglist_db():
 with shelve.open('shopping_list.db', 'r') as db:
  stocked = [f"{d['name']} that is a {d['category']}" for d in db['items'] if d['status'] == 'In Stock']
  print('ingredients are ', stocked)
  return 'Using these ingredients: ' + ', '.join(stocked)

# IF SOMEONE CLICKED ON 'GENERATE MEAL WITH INGREDIENTS'
def gen_prompt(info, gentype, stocked):
 print('into userforminput', info)
 mealgentype = f'{'a meal' if gentype else '3 meals, one for breakfast, one for lunch and one for dinner'}'
 # https://stackoverflow.com/questions/1679384/converting-dictionary-to-list
 extra = f'{f'Additional notes from user are: "{info[2]}."' if info[2] != '' else ''}'
 diet = f'{'anything related to sustainable diets,' if 'No preference' in info[1] else info[1]}'
 allergy = f'{'nothing' if 'None' in info[0] else info[0]}'
 details = f'User is allergic to {allergy}. Create {mealgentype} that is {diet}. {extra}'
 try:
  if stocked:
   details += f" {accessing_shoppinglist_db()}"
 except:
  print('stocked requires a boolean data type')
  return 'ERROR: stocked requires a boolean data type'
 return details

class Recipes:
 def __init__(self):
  self.__donotinclude = ''
  self.prev_list = None

 def save(self, prev):
  self.prev_list = prev

 async def meal_plan(self, info, stocked):
  prompt = f"""{gen_prompt(info, False, stocked)} {self.__donotinclude}
   \n'**< breakfast or dinner or lunch etc and mealname >:**\n\n**Ingredients:** < ingredients >\n\n**Equipment:** < equipment >\n\n**Instructions:** < instructions >\nEnd of meal.
  After generating those, tell the user the names of the meal only in this format: 
  ' List: < insert meal name 1 here >, < insert meal name 2 here >. '"""
  response = model.generate_content(prompt).text
  text_split = response.split('List: ')
  self.__donotinclude = text_split[1]

  meal_names = i.get_listofmealnames(text_split[1])
  print('your mealnames', text_split[1])
  img_addresses = await i.fetch_images_for_meals(meal_names)
  dishes = await return_markdown(text_split[0])
  print('printing dishess!!', dishes)
  self.__donotinclude = text_split[1]
  loadedList = []

  for index in range(0, len(meal_names)):
   dic = {
    'mealname': meal_names[index],
    'meal': dishes[index],
    'imgurl': img_addresses[index],
   }
   loadedList.append(dic)

  return loadedList

 async def loaded(self):
  prompt = f"""create 6 meals thats either breakfast, lunch, or dinner that's either paleo, mediterranean, or vegan.
  {self.nomore(self.__donotinclude)}
   \n'**Meal for <breakfast/lunch etc>:** < mealname >\n\n**Ingredients:** < ingredients >\n\n**Equipment:** < equipment >\n\n**Instructions:** < instructions >\nEnd of meal.'
   After generating them, tell the user the names of the meal only in this format: 
   ' List: < insert meal name 1 here >, < insert meal name 2 here >, ' """
  text = model.generate_content(prompt).text
  text_split = text.split('List: ')

  meal_names = i.get_listofmealnames(text_split[1])
  print('your mealnames', text_split[1])
  dishes = await return_markdown(text_split[0])
  print('printing dishess!!',dishes)
  img_addresses = await i.fetch_images_for_meals(meal_names)

  self.__donotinclude = text_split[1]
  loadedList = []

  for index in range(0, len(meal_names)):
   dic = {
    'mealname': meal_names[index],
    'meal': dishes[index],
    'imgurl': img_addresses[index],
   }
   loadedList.append(dic)

  return loadedList

 def nomore(self, text):
  return f'{'using this format:' if self.__donotinclude == '' else f"do not include {text}." }'

 def mdtohtml(self, md):
  return markdown.markdown(md)

 def listtojson(self, str_list):
  return json.dumps(str_list)

 def jsonload(self, obj):
  return json.loads(obj)
