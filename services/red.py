import requests
import re
import base64
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN_URL = os.getenv("TOKEN_URL")
PREDICTION_URL = os.getenv("PREDICTION_URL")

def get_token():
  response = requests.get(TOKEN_URL)
  soup = BeautifulSoup(response.text, 'html.parser')

  for script in soup.find_all('script'):
    if script.string:
        match = re.search(r"\$jwt\s*=\s*'([^']+)'", script.string)
        if match:
            jwt = match.group(1)
            break  # Sale cuando encuentra el primero
  if jwt:
    jwt_decoded = base64.b64decode(jwt)
    return jwt_decoded.decode('utf-8')
  return None

def get_prediction(jwt, codsimt):
  response = requests.get(f"{PREDICTION_URL}?t={jwt}&codsimt={codsimt}&codser=")
  return response.json()