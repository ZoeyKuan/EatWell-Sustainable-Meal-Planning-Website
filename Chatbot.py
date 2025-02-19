import google.generativeai as genai

class Chatbot:
	def __init__(self):
		genai.configure(api_key="AIzaSyArgfuunvoAXWkYrCrhexEFFE-9cAC5D4I")
		self.__model = genai.GenerativeModel('gemini-1.5-flash')
	def bot_replies(self, userinput):
		prompt = f'''You are an AI assistant of a meal planning website called EatWell and you are to assume all messages are related to EatWell.
		 The meal planning website offers sustainable diets like Paleo, Mediterranean and Vegan which all recipes are curated by AI. 
		The goal of the site is to improve overall health and reduce	carbon output.
		 We offer a free version with essential features and a premium plan for advanced meal planning tools.
		The belief of this website is that we can improve the health of individuals with chronic diseases. 
		Pages are Browse Recipes (can edit, delete, and save recipes as well as create AI meal by filling out a form ),
		 Calendar (displays all saved recipes from browse recipes), Shopping Cart selling organic fresh produce in singapore, and
		 Ingredients List (help users track their ingredients like whats in stock +
		 what the AI can make if the user asks the AI to do so)\n
		here is a message from the user: {userinput}
		'''
		reply = self.__model.generate_content(prompt)
		return {'role': 'chatbot', 'reply': reply.text}

chatbot = Chatbot()