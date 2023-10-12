import openai
import bigcommerce
import requests
import random
import time
import datetime

config = {
    "openai_api_key": "sk-xxx",
    "bigcommerce_api_key": "xxx",
    "bigcommerce_store_hash": "xxx",
    "bigcommerce_client_id": "xxx"
}

api = bigcommerce.api.BigcommerceApi(
    client_id=config["bigcommerce_client_id"],
    store_hash=config["bigcommerce_store_hash"],
    access_token=config["bigcommerce_api_key"]
)

openai.api_key = config["openai_api_key"]

def generate_product(category, inputs):

    query = f"Generate a product name: , description: , price: , and weight: for a {category} product based on these inputs: {inputs}\n\nExample output:\nProduct name: Alpine Explorer Men's Outdoor Jacket\nDescription: Crafted for those who love the great outdoors, the Alpine Explorer Men's Outdoor Jacket is a stylish fusion of form and function. Made with a blend of high-performance materials, it ensures optimal warmth and water-resistance while providing full-range mobility.\nPrice: 249.99\nWeight: 2.5\n\nPlease only output in this format. Make sure to not include dollar signs on the prices."
    try:

        response = openai.ChatCompletion.create(
            messages=[
                {"role": "system", "content": "You are a creative assistant who can generate products for any category based on some inputs."},
                {"role": "user", "content": query}
            ], 
            model="gpt-4"
        )
    except openai.error.OpenAIError as e:
        print(f"An error occurred while using the OpenAI API: {e}")
        return None

    product_data = {}

    if hasattr(response, "choices"):

        choices = response.choices

        valid_choices = [choice for choice in choices if choice.finish_reason in ["stop", "length"]]

        chosen_choice = valid_choices[0] 

        message = chosen_choice.message

        if message.role == "assistant":

            lines = message.content.split("\n")

            if len(lines) == 4 and all(line.startswith(("Product name", "Description", "Price", "Weight")) for line in lines):

                product_data["name"] = lines[0].split(":")[1].strip()
                product_data["description"] = lines[1].split(":")[1].strip()
                try:
                    product_data["price"] = float(lines[2].split(":")[1].strip())
                except ValueError as e:
                    print(f"An error occurred while parsing the price: {e}")
                    return None
                try:
                    product_data["weight"] = float(lines[3].split(":")[1].strip())
                except ValueError as e:
                    print(f"An error occurred while parsing the weight: {e}")
                    return None
                return product_data
            else:

                print(f"The response from the OpenAI API was not valid: {message.content}")
                return None
        else:

            print(f"The response from the OpenAI API was not from an assistant: {message.content}")
            return None
    else:

        print(f"The response from the OpenAI API was empty or invalid: {response}")
        return None
def get_or_create_category(category):
    # Get a list of all the categories and their IDs using the BigCommerce API
    categories = api.Categories.iterall()
    # Loop through the categories and compare the names with the input
    for cat in categories:
        # If there is a match, return the ID
        if cat.name == category:
            return cat.id
    # If there is no match, create a new category using the BigCommerce API and return the new ID
    new_category = api.Categories.create(name=category)
    return new_category.id

def create_product(product_data, category):
    # Create a product object with the required fields using the BigCommerce API Python Client
    try: # Added a try-except block to handle any errors from the BigCommerce API
        product = api.Products.create(
            categories=[get_or_create_category(category)], # Use the get_or_create_category function to get the category ID from the category name
            name=product_data["name"],
            description=product_data["description"],
            price=product_data["price"],
            type="physical",
            availability="available",
            weight=product_data["weight"]
            
        )
        # Return the product object
        return product
    except bigcommerce.exception.ClientRequestException as e: # Added an exception handler for ClientRequestException, which is raised when there is an error in the request parameters or headers
        print(f"An error occurred while creating the product on BigCommerce: {e}")
        return None
    
def generate_image(description):

    try: 
        image = openai.Image.create(
            prompt=description,
            size="512x512", 
        )

        return image.data[0].url 
    except openai.error.OpenAIError as e: 
        print(f"An error occurred while generating an image from OpenAI: {e}")
        return None

def create_image(image_url, product_id):

    response = requests.get(image_url)
    if response.status_code == 200: 

        try: 

            payload = {
                'image_file': ('image.jpg', response.content, 'image/jpeg') 
            }

            headers = {
                'X-Auth-Client': config["bigcommerce_client_id"],
                'X-Auth-Token': config["bigcommerce_api_key"],
            }

            response = requests.post(f'https://api.bigcommerce.com/stores/{config["bigcommerce_store_hash"]}/v3/catalog/products/{product_id}/images', files=payload, headers=headers)

            if response.status_code == 200: 
                print(f"Image created successfully!")
            else: 
                print(f"An error occurred while creating an image on BigCommerce: {response.status_code} {response.text}")
        except bigcommerce.exception.ClientRequestException as e: 
            print(f"An error occurred while creating an image on BigCommerce: {e}")
            return None
    else: 
        print(f"An error occurred while downloading the image from OpenAI: {response.status_code}")
        return None

def generate_user():

    user_data = {}

    user_data["name"] = random.choice(["John", "Jane", "Jack", "Jill", "James", "Jenny", "Jeff", "Julia", "Jake", "Jess"]) + " " + random.choice(["Smith", "Jones", "Brown", "Wilson", "Miller", "Davis", "Taylor", "Clark", "Lee", "White"])
    user_data["email"] = user_data["name"].lower().replace(" ", ".") + str(random.randint(1,1000)) + "@example.com"

    return user_data

def create_user(user_data):

    try: 
        user = api.Customers.create(
            first_name=user_data["name"].split()[0],
            last_name=user_data["name"].split()[1],
            email=user_data["email"]
        )

        return user
    except bigcommerce.exception.ClientRequestException     as e: 
        print(f"An error occurred while creating the user on BigCommerce: {e}")
        return None



def generate_order(user_id, product_ids):

    order_data = {}

    # Use a static list of order status IDs instead of polling from the API
    order_status_ids = [2, 9, 10]
    order_data["status_id"] = random.choice(order_status_ids)

    # Use today's date plus or minus a few weeks as the order date
    today = datetime.date.today()
    delta = datetime.timedelta(days=random.randint(-21, 21))
    order_date = today + delta

    # Format the order date as a valid RFC-2822 date using the email.utils module
    import email.utils
    # Convert the order date to a time.struct_time object using the timetuple method
    order_date_struct = order_date.timetuple()
    # Convert the time.struct_time object to a float representing seconds since epoch using the time.mktime function
    order_date_seconds = time.mktime(order_date_struct)
    # Format the float as a valid RFC-2822 date using the email.utils.formatdate function
    order_date_rfc = email.utils.formatdate(timeval=order_date_seconds, localtime=False, usegmt=True)
    order_data["date_created"] = order_date_rfc

    # Remove the prices and product names from the order data
    products = []
    num_products = random.randint(1, len(product_ids))
    for i in range(num_products):
        product_id = random.choice(product_ids)
        quantity = random.randint(1, 5)
        products.append({
            "product_id": product_id,
            "quantity": quantity
        })

    # Remove the tax amount from the order data
    order_data["shipping_cost"] = random.choice([0, 5.99, 9.99, 14.99])

    # Generate a billing address for the order using the user's name and email
    user = api.Customers.all(min_id=user_id)[0]
    first_name, last_name = user.first_name, user.last_name
    email = user.email

    # Use a dictionary of cities and states that go together instead of selecting them randomly
    city_state_dict = {
        "Austin": "Texas",
        "Boston": "Massachusetts",
        "Chicago": "Illinois",
        "Denver": "Colorado",
        "New York": "New York"
    }
    city, state = random.choice(list(city_state_dict.items()))
    
    street_1 = random.choice(["123 Main Street", "456 Elm Street", "789 Pine Street"])
    zip_code = random.randint(10000, 99999)
    country = "United States"
    country_iso2 = "US"
    
    billing_address = {
        "first_name": first_name,
        "last_name": last_name,
        "company": "",
        "street_1": street_1,
        "street_2": "",
        "city": city,
        "state": state,
        "zip": zip_code,
        "country": country,
        "country_iso2": country_iso2,
        "phone": "",
        "email": email
    }

    # Add the billing address to the order data
    order_data["billing_address"] = billing_address

    return order_data, products

    # Add the billing address to the order data
    order_data["billing_address"] = billing_address

    return order_data, products

def create_order(order_data, user_id, products):

    try:
        # Use the api.Orders.create method instead of the create_from_dict method
        order = api.Orders.create(
            customer_id=user_id,
            date_created=order_data["date_created"],
            status_id=order_data["status_id"],
            products=products,
            billing_address=order_data["billing_address"]
        )

        return order
    except bigcommerce.exception.ClientRequestException as e: 
        print(f"An error occurred while creating the order on BigCommerce: {e}")
        return None


def main():

    print("Welcome to the BigCommerce Product Generator!")
    print("This application will help you create products, users, and orders on your BigCommerce store using the ChatGPT and DALL-E APIs.")

    category = input("Please enter a product category name: ")
    inputs = input("Please enter any other inputs you want to use for generating products (separated by commas): ")

    num_products = int(input("Please enter the number of products you want to generate and create: "))
    num_users = int(input("Please enter the number of users you want to generate and create: "))
    num_orders_per_user = int(input("Please enter the number of orders per user you want to generate and create: "))

    product_ids = []
    for i in range(num_products):
        print(f"Generating product {i+1}...")

        product_data = generate_product(category, inputs)
        if product_data: 

            product = create_product(product_data, category)
            if product: 

                print(f"Product {i+1} created successfully!")
                print(f"Product ID: {product.id}")
                print(f"Product Name: {product.name}")
                print(f"Product Description: {product.description}")
                print(f"Product Price: {product.price}")
                print(f"Product Weight: {product.weight}")

                image_url = generate_image(product.description)
                if image_url: 

                    image = create_image(image_url, product.id)
                    if image: 

                        print(f"Image created successfully!")

                else:
                    print(f"Image generation failed!")

                product_ids.append(product.id)

            else:
                print(f"Product {i+1} creation failed!")
        else:
            print(f"Product {i+1} generation failed!")

    user_ids = []
    for i in range(num_users):
        print(f"Generating user {i+1}...")

        user_data = generate_user()
        if user_data:

            user = create_user(user_data)
            if user:

                print(f"User {i+1} created successfully!")
                print(f"User ID: {user.id}")
                print(f"User Name: {user.first_name} {user.last_name}")
                print(f"User Email: {user.email}")

                user_ids.append(user.id)

            else:
                print(f"User {i+1} creation failed!")
        else:
            print(f"User {i+1} generation failed!")

    order_ids = []
    for user_id in user_ids:
        for i in range(num_orders_per_user):
            print(f"Generating order {i+1} for user {user_id}...")

            order_data, products = generate_order(user_id, product_ids)
            if order_data and products:

                order = create_order(order_data, user_id, products)
                if order:

                    print(f"Order {i+1} for user {user_id} created successfully!")
                    print(f"Order ID: {order.id}")
                    print(f"Order Date: {order.date_created}")
                    print(f"Order Status: {order.status_id}")
                    print(f"Order Subtotal: {order.subtotal_inc_tax}")
                    print(f"Order Shipping Cost: {order.shipping_cost_inc_tax}")
                    print(f"Order Tax Amount: {order.total_tax}")
                    print(f"Order Total: {order.total_inc_tax}")
                    print(f"Order Products:")
                    for product in order.products():
                        print(f"- Product ID: {product.product_id}")
                        print(f"- Product Name: {product.name}")
                        print(f"- Product Quantity: {product.quantity}")
                        print(f"- Product Price: {product.price_inc_tax}")

                    order_ids.append(order.id)

                else:
                    print(f"Order {i+1} for user {user_id} creation failed!")
            else:
                print(f"Order {i+1} for user {user_id} generation failed!")

    print("Thank you for using the BigCommerce Product Generator!")
main()
