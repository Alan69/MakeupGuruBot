import telebot
import requests
import random
import json
import schedule
import time
import threading
from dotenv import load_dotenv
import os

# Replace 'YOUR_API_TOKEN' with the API token you got from BotFather
load_dotenv()

# Get the API token from the environment variables
API_TOKEN = os.getenv('API_TOKEN')

bot = telebot.TeleBot(API_TOKEN)

# Base URL of the Makeup API
MAKEUP_API_URL = "http://makeup-api.herokuapp.com/api/v1/products.json"

# File to store user preferences (you can use a database for more complex use cases)
USER_PREFERENCES_FILE = 'user_preferences.json'

SKIN_TYPES = ['oily', 'dry', 'combination', 'sensitive', 'normal']

# Load user preferences from the file
def load_user_preferences():
    try:
        with open(USER_PREFERENCES_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Save user preferences to the file
def save_user_preferences(preferences):
    with open(USER_PREFERENCES_FILE, 'w') as file:
        json.dump(preferences, file)

# Initialize preferences
user_preferences = load_user_preferences()

@bot.message_handler(commands=['skin_types'])
def list_skin_types(message):
    reply = "Available Skin Types:\n" + "\n".join(SKIN_TYPES)
    bot.reply_to(message, reply)

# Function to fetch and extract unique values for tags, brands, product types, and categories
def fetch_makeup_data():
    response = requests.get(MAKEUP_API_URL)
    products = response.json()
    
    tags = set()
    brands = set()
    product_types = set()
    categories = set()
    
    for product in products:
        if product.get("tag_list"):
            tags.update(product["tag_list"])
        if product.get("brand"):
            brands.add(product["brand"])
        if product.get("product_type"):
            product_types.add(product["product_type"])
        if product.get("category"):
            categories.add(product["category"])
    
    return sorted(tags), sorted(brands), sorted(product_types), sorted(categories)

# Fetch data
TAGS, BRANDS, PRODUCT_TYPES, CATEGORIES = fetch_makeup_data()

# Welcome message
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "Welcome to the Makeup Product Finder Bot! 💄✨\n"
        "I can help you find makeup products and get details about them.\n"
        "Type /help to see the available commands."
    )
    bot.reply_to(message, welcome_text)

# Help message
@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "Here are some commands you can use:\n"
        "/find <brand> - Find products by brand (e.g., /find colourpop)\n"
        "/product <id> - Get details of a product by its ID\n"
        "/random - Get a random makeup product suggestion\n"
        "/tags - List all available tags\n"
        "/brands - List all available brands\n"
        "/product_types - List all available product types\n"
        "/categories - List all available categories\n"
        "/category <name> <type> - Find products by category and type (e.g., /category powder blush)\n"
        "/tag <name> <type> - Find products by tag and type (e.g., /tag vegan blush)\n"
        "/set_preferences <skin_type> <brand> <category> - Set your preferences\n"
        "/recommendations - Get personalized recommendations\n"
        "/skin_types - Get skin types"
    )
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['set_preferences'])
def set_preferences(message):
    try:
        parts = message.text.split()
        if len(parts) < 4:
            bot.reply_to(message, "Please specify your skin type, favorite brand, and product category (e.g., /set_preferences oily colourpop lipstick).")
            return
        
        user_id = str(message.chat.id)
        skin_type = parts[1].lower()
        favorite_brand = parts[2].lower()
        product_category = parts[3].lower()

        user_preferences[user_id] = {
            "skin_type": skin_type,
            "favorite_brand": favorite_brand,
            "product_category": product_category
        }
        save_user_preferences(user_preferences)
        bot.reply_to(message, "Preferences saved successfully!")
    except Exception as e:
        bot.reply_to(message, "Error setting preferences. Please try again.")

# Command to get personalized recommendations
@bot.message_handler(commands=['recommendations'])
def get_recommendations(message):
    user_id = str(message.chat.id)
    if user_id not in user_preferences:
        bot.reply_to(message, "You haven't set your preferences yet. Use /set_preferences to do so.")
        return

    preferences = user_preferences[user_id]
    favorite_brand = preferences["favorite_brand"]
    product_category = preferences["product_category"]

    response = requests.get(f"{MAKEUP_API_URL}?brand={favorite_brand}&product_type={product_category}")
    products = response.json()

    if not products:
        bot.reply_to(message, f"No products found for brand '{favorite_brand}' and category '{product_category}'.")
        return

    # Show up to 5 products
    reply = f"Recommended products for you ({preferences['skin_type']} skin type, {favorite_brand} brand, {product_category} category):\n"
    for product in products[:5]:
        reply += f"{product['name']} - ${product['price']} {product['currency']}\n"
        reply += f"More info: {product['product_link']}\n\n"

    bot.reply_to(message, reply)

# List of beauty tips
BEAUTY_TIPS = [
    "Drink plenty of water to keep your skin hydrated.",
    "Always remove your makeup before going to bed.",
    "Use a broad-spectrum sunscreen every day, even on cloudy days.",
    "Exfoliate your skin regularly to remove dead skin cells.",
    "Choose skincare products that suit your skin type for the best results."
]

# Function to send a random beauty tip
def send_beauty_tip():
    for user_id in user_preferences:
        bot.send_message(user_id, random.choice(BEAUTY_TIPS))

# Function to keep the scheduler running
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Start the scheduler in a separate thread
threading.Thread(target=run_scheduler).start()

# Command to list all tags
@bot.message_handler(commands=['tags'])
def list_tags(message):
    reply = "Available Tags:\n" + "\n".join(TAGS)
    bot.reply_to(message, reply)

# Command to list all brands
@bot.message_handler(commands=['brands'])
def list_brands(message):
    reply = "Available Brands:\n" + "\n".join(BRANDS)
    bot.reply_to(message, reply)

# Command to list all product types
@bot.message_handler(commands=['product_types'])
def list_product_types(message):
    reply = "Available Product Types:\n" + "\n".join(PRODUCT_TYPES)
    bot.reply_to(message, reply)

# Command to list all categories
@bot.message_handler(commands=['categories'])
def list_categories(message):
    reply = "Available Categories:\n" + "\n".join(CATEGORIES)
    bot.reply_to(message, reply)

# Find products by brand
@bot.message_handler(commands=['find'])
def find_products(message):
    try:
        brand = message.text.split()[1]  # Get the brand from the user input
        response = requests.get(f"{MAKEUP_API_URL}?brand={brand}")
        products = response.json()

        if not products:
            bot.reply_to(message, f"No products found for brand '{brand}'.")
            return

        # Show up to 5 products
        reply = f"Products from '{brand}':\n"
        for product in products[:5]:
            reply += f"{product['name']} - ${product['price']} {product['currency']}\n"
            reply += f"More info: {product['product_link']}\n\n"

        bot.reply_to(message, reply)
    except IndexError:
        bot.reply_to(message, "Please specify a brand name (e.g., /find colourpop).")

# Get product details by ID
@bot.message_handler(commands=['product'])
def get_product_details(message):
    try:
        product_id = message.text.split()[1]  # Get the product ID from the user input
        response = requests.get(f"http://makeup-api.herokuapp.com/api/v1/products/{product_id}.json")
        product = response.json()

        if 'id' not in product:
            bot.reply_to(message, "Product not found. Please check the ID and try again.")
            return

        # Construct the product details message
        reply = f"**{product['name']}**\n"
        reply += f"Brand: {product['brand']}\n"
        reply += f"Price: {product['price_sign']}{product['price']} {product['currency']}\n"
        reply += f"Description: {product['description']}\n"
        reply += f"Product Link: {product['product_link']}\n"

        # Send the product image if available
        if product['image_link']:
            bot.send_photo(message.chat.id, product['image_link'], caption=reply)
        else:
            bot.reply_to(message, reply)
    except IndexError:
        bot.reply_to(message, "Please specify a product ID (e.g., /product 1048).")

# Find products by category
@bot.message_handler(commands=['category'])
def find_by_category(message):
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "Please specify both a category and a product type (e.g., /category powder blush).")
            return
        
        category = parts[1].lower()
        product_type = parts[2].lower()
        response = requests.get(f"{MAKEUP_API_URL}?product_category={category}&product_type={product_type}")
        products = response.json()

        if not products:
            bot.reply_to(message, f"No products found for category '{category}' and type '{product_type}'.")
            return

        # Show up to 5 products
        reply = f"Products in category '{category}' and type '{product_type}':\n"
        for product in products[:5]:
            reply += f"{product['name']} - ${product['price']} {product['currency']}\n"
            reply += f"More info: {product['product_link']}\n\n"

        bot.reply_to(message, reply)
    except IndexError:
        bot.reply_to(message, "Please specify a category and type (e.g., /category powder blush).")

# Find products by tag
@bot.message_handler(commands=['tag'])
def find_by_tag(message):
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "Please specify both a tag and a product type (e.g., /tag vegan blush).")
            return
        
        tag = parts[1].lower()
        product_type = parts[2].lower()
        response = requests.get(f"{MAKEUP_API_URL}?product_tags={tag}&product_type={product_type}")
        products = response.json()

        if not products:
            bot.reply_to(message, f"No products found for tag '{tag}' and type '{product_type}'.")
            return

        # Show up to 5 products
        reply = f"Products with tag '{tag}' and type '{product_type}':\n"
        for product in products[:5]:
            reply += f"{product['name']} - ${product['price']} {product['currency']}\n"
            reply += f"More info: {product['product_link']}\n\n"

        bot.reply_to(message, reply)
    except IndexError:
        bot.reply_to(message, "Please specify a tag and type (e.g., /tag vegan blush).")

# Suggest a random product
@bot.message_handler(commands=['random'])
def random_product(message):
    response = requests.get(MAKEUP_API_URL)
    products = response.json()

    if not products:
        bot.reply_to(message, "No products available right now. Try again later.")
        return

    product = random.choice(products)

    # Check if the image link is a full URL, if not, add "https:"
    image_link = product['image_link']
    if image_link.startswith("//"):
        image_link = "https:" + image_link

    # Construct the product details message
    reply = f"**{product['name']}**\n"
    reply += f"Brand: {product['brand']}\n"
    reply += f"Price: {product['price_sign']}{product['price']} {product['currency']}\n"
    reply += f"Description: {product['description']}\n"
    reply += f"Product Link: {product['product_link']}\n"

    # Send the product image if available
    if image_link:
        bot.send_photo(message.chat.id, image_link, caption=reply)
    else:
        bot.reply_to(message, reply)


# Schedule beauty tips to be sent daily at a specific time
schedule.every().day.at("10:00").do(send_beauty_tip)

# Polling loop to keep the bot running
bot.polling()
