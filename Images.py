import asyncio, aiohttp
import google.generativeai as genai

genai.configure(api_key="AIzaSyArgfuunvoAXWkYrCrhexEFFE-9cAC5D4I")
model = genai.GenerativeModel('gemini-1.5-flash')

class Images:
 def __init__(self):
  self.searchAPI = 'b276cd4d18f1e4e40'
  self.ZOEY_APIKEY = 'AIzaSyAeAwZr8nuyspgq-R0m3oznPPJSn0g6ypI'

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
    print(data)
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