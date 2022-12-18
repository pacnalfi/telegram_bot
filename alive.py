from flask import Flask, json, request
from threading import Thread
from replit import db
import os

app = Flask('')

@app.route('/')
def home():
    return "Hello. I am alive!"

@app.route('/0')
def home0():
    return "Hello. I am alive!"
    
def run():
  app.run(port='3000', host='0.0.0.0')

def keep_alive():
    t = Thread(target=run)
    t.start()