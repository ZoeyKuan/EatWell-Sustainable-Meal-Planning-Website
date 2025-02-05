import google.generativeai as genai
import markdown, json

genai.configure(api_key="AIzaSyArgfuunvoAXWkYrCrhexEFFE-9cAC5D4I")
model = genai.GenerativeModel('gemini-1.5-flash')

# so when we click on a meal, it should show the markdown text instead of the html or text content
def return_markdown(text):
 new_text = text.split('End of meal.')
 print('hopefully is markdwon',new_text)
 new_text.pop(-1)
 return new_text

def gen_prompt(info, gentype):
 print('into userforminput', info)
 mealgentype = f'{'a meal' if gentype else '3 meals, one for breakfast, one for lunch and one for dinner'}'
 # https://stackoverflow.com/questions/1679384/converting-dictionary-to-list
 extra = f'{f'Additional notes from user are: "{info[2]}."' if info[2] != '' else ''}'
 diet = f'{'anything related to sustainable diets,' if 'No preference' in info[1] else info[1]}'
 allergy = f'{'nothing' if 'None' in info[0] else info[0]}'
 details = f'User is allergic to {allergy}. Create {mealgentype} that is {diet}. {extra}'
 return details

class Recipes:
 def __init__(self):
  self.__donotinclude = ''
  self.prev_list = None

 def save(self, prev):
  self.prev_list = prev

 def one_meal_form(self, info):
  mdtext = model.generate_content(f"""{gen_prompt(info, True)} {self.__donotinclude}
   \n**Mealname:**\n\n**Ingredients:** < ingredients >\n\n**Equipment:** < equipment >\n\n**Instructions:** < instructions >\n\n
  After generating those, tell the user the names of the meal only in this format: 
  ' List: < insert meal name 1 here >, < insert meal name 2 here >. '""").text
  print(mdtext)
  text = mdtext.split('List: ')
  # to_html = markdown.markdown(text[0])
  self.__donotinclude = text[1]
  return text[0]

 def meal_plan(self, info):
  prompt = f"""{gen_prompt(info, False)} {self.__donotinclude}
   \n'**< breakfast or dinner or lunch etc and mealname >:**\n\n**Ingredients:** < ingredients >\n\n**Equipment:** < equipment >\n\n**Instructions:** < instructions >\nEnd of meal.
  After generating those, tell the user the names of the meal only in this format: 
  ' List: < insert meal name 1 here >, < insert meal name 2 here >. '"""
  response = model.generate_content(prompt).text
  text_split = response.split('List: ')
  self.__donotinclude = text_split[1]
  return return_markdown(text_split[0])

 def loaded(self):
  prompt = f"""create 5 cheap but completely different meals that's either paleo, mediterranean, or vegan.
  {self.nomore(self.__donotinclude)}
   \n'**Meal:** < mealname >\n\n**Ingredients:** < ingredients >\n\n**Equipment:** < equipment >\n\n**Instructions:** < instructions >\nEnd of meal.'
   After generating the 6 meals, tell the user the names of the meal only in this format: 
   ' List: < insert meal name 1 here >, < insert meal name 2 here >. ' """
  text = model.generate_content(prompt).text
  text_split = text.split('List: ')
  self.__donotinclude = text_split[1]
  print('from do not include', self.__donotinclude)
  return return_markdown(text_split[0])

 def nomore(self, text):
  return f'{'using this format:' if self.__donotinclude == '' else f"do not include {text}." }'

 def mdtohtml(self, md):
  return markdown.markdown(md)

 def listtojson(self, str_list):
  return json.dumps(str_list)

 def jsonload(self, obj):
  return json.loads(obj)