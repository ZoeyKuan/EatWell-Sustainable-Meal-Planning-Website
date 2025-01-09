import google.generativeai as genai
import markdown

genai.configure(api_key="AIzaSyArgfuunvoAXWkYrCrhexEFFE-9cAC5D4I")
model = genai.GenerativeModel('gemini-1.5-flash')

# splitting to ensure generation of separate meals
def markdown_to_html(md):
 html_list = []
 markdown_text = md.split('End of meal.')
 markdown_text.pop(-1)
 for i in markdown_text:
  html_list.append(markdown.markdown(i).replace('\n',''))
 # print('replacing every md list into html', html_list)
 return html_list

def gen_prompt(info, gentype):
 print('into userforminput', info)
 mealgentype = f'{'a meal' if gentype else '3 meals, one for breakfast, one for lunch and one for dinner'}'
 # https://stackoverflow.com/questions/1679384/converting-dictionary-to-list
 extra = f'{f'Additional notes from user are: "{info[2]}."' if info[2] != '' else ''}'
 diet = f'{'anything related to sustainable diets' if 'No preference' in info[1] else info[1]}'
 allergy = f'{'anything related to sustainable diets' if 'None' in info[0] else info[0]}'
 details = f'User is allergic to {allergy}. Create {mealgentype} that is {diet}. {extra}'
 return details

class Recipes:
 def __init__(self):
  self.__prev = None
  self.__prevMeal = None
  self.__prevPlan = None

 def one_meal_form(self, info):
  mdtext = model.generate_content(f"""{gen_prompt(info, True)}
   do not include {self.__prevMeal} and make a new one but use this format:
   \n** mealname **\n\n**Ingredients:** < ingredients >\n\n**Equipment:** < equipment >\n\n**Instructions:** < instructions >\n\n
  After generating those, tell the user the names of the meal only in this format: 
  ' List: < insert meal name 1 here >, < insert meal name 2 here >. '""").text
  text_split = mdtext.split('List: ')
  to_html = markdown.markdown(text_split[0])
  self.__prevMeal = text_split[1]
  return to_html

 def meal_plan(self, info):
  prompt = f"""{gen_prompt(info, False)} 
  do not include {self.__prevPlan} and make a new one but use this format:
   \n'** < meal > **\n\n**Ingredients:** < ingredients >\n\n**Equipment:** < equipment >\n\n**Instructions:** < instructions >\nEnd of meal.
  After generating those, tell the user the names of the meal only in this format: 
  ' List: < insert meal name 1 here >, < insert meal name 2 here >. '"""
  response = model.generate_content(prompt).text
  text_split = response.split('List: ')
  self.__prevPlan = text_split[1]
  return markdown_to_html(text_split[0])

 def loaded(self):
  prompt = f"""create 6 cheap but completely different meals that's either paleo, mediterranean, or vegan.
   do not include {self.__prev} and make a new one but you must use this format:
   \n'< mealname >\n\n**Ingredients:** < ingredients >\n\n**Equipment:** < equipment >\n\n**Instructions:** < instructions >\nEnd of meal.'
   After generating the 6 meals, tell the user the names of the meal only in this format: 
   ' List: < insert meal name 1 here >, < insert meal name 2 here >. ' """
  text = model.generate_content(prompt).text
  text_split = text.split('List: ')
  self.__prev = text_split[1]
  # print('start', self.__prev, 'end')
  return markdown_to_html(text_split[0])

