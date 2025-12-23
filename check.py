
from urllib.parse import quote_plus
import pandas as pd
from flask import Flask, request, render_template, jsonify
import urllib

product_url="www.google.com"

question="prod info BATTERY-964108"
encoded_url = urllib.parse.quote(product_url)
print(encoded_url)