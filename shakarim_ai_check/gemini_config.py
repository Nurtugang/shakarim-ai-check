import os
from google import genai
from dotenv import load_dotenv
from google.genai import types

load_dotenv()

GEMINI_API_KEY = "AIzaSyBGimDikmqQjpbdg-Gb81FI4IGfJPH82es"
client = genai.Client(api_key=GEMINI_API_KEY)