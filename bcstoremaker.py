# Import the required packages and libraries
import openai
import bigcommerce
import requests

# Create a configuration file that stores the API keys and store hash
config = {
    "openai_api_key": "sk-xxx",
    "bigcommerce_api_key": "xxx",
    "bigcommerce_store_hash": "xxx",
    "bigcommerce_client_id": "xxx"
}

# Connect to the BigCommerce API using OAuth
api = bigcommerce.api.BigcommerceApi(
    client_id=config["bigcommerce_client_id"],
    store_hash=config["bigcommerce_store_hash"],
    access_token=config["bigcommerce_api_key"]
)

# Connect to the OpenAI API using your secret key
openai.api_key = config["openai_api_key"]

# Write a function that takes a product category name and other inputs from the user and uses the ChatGPT API to generate a product name, description, price, and weight
def generate_product(category, inputs):
    # Use the ChatCompletion endpoint with the gpt-4 model to get natural language responses from ChatGPT
    query = f"Generate a product name: , description: , price: , and weight: for a {category} product based on these inputs: {inputs}\n\nExample output:\nProduct name: Alpine Explorer Men's Outdoor Jacket\nDescription: Crafted for those who love the great outdoors, the Alpine Explorer Men's Outdoor Jacket is a stylish fusion of form and function. Made with a blend of high-performance materials, it ensures optimal warmth and water-resistance while providing full-range mobility.\nPrice: 249.99\nWeight: 2.5\n\nPlease only output in this format. Make sure to not include dollar signs on the prices."
    try:
        # Add a system message to provide some context and instructions to the model
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
    # Parse the response and return a dictionary with the product data
    product_data = {}
    # Check if the response object has the choices attribute
    if hasattr(response, "choices"):
        # Get the list of choices from the response
        choices = response.choices
        # Filter out any choices that have an incomplete or invalid finish reason
        valid_choices = [choice for choice in choices if choice.finish_reason in ["stop", "length"]]
        # Choose one of the valid choices, either by using the first one or by using some criteria
        chosen_choice = valid_choices[0] # This is a simple example, you can use other criteria to choose the best choice
        # Get the message from the chosen choice
        message = chosen_choice.message
        # Check if the message role is assistant
        if message.role == "assistant":
            # Split the message content by newline characters to get the lines
            lines = message.content.split("\n")
            # Check if the lines have the expected format and length of 4
            if len(lines) == 4 and all(line.startswith(("Product name", "Description", "Price", "Weight")) for line in lines):
                # Extract the product data from each line by splitting by colon and stripping whitespace
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
                # The lines do not have the expected format or length, so return None
                print(f"The response from the OpenAI API was not valid: {message.content}")
                return None
        else:
            # The message role is not assistant, so return None
            print(f"The response from the OpenAI API was not from an assistant: {message.content}")
            return None
    else:
        # The response object does not have the choices attribute, so return None
        print(f"The response from the OpenAI API was empty or invalid: {response}")
        return None

# Write a function that takes a category name as an input and returns the category ID as an output
def get_or_create_category(category):
    # Get a list of all the categories and their IDs using the BigCommerce API
    categories = api.Categories.all()
    # Loop through the categories and compare the names with the input
    for cat in categories:
        # If there is a match, return the ID
        if cat.name == category:
            return cat.id
    # If there is no match, create a new category using the BigCommerce API and return the new ID
    new_category = api.Categories.create(name=category)
    return new_category.id

# Write a function that takes the product data generated by ChatGPT and uses the BigCommerce API to create a product on your BigCommerce store
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

# Write a function that takes a product description and uses the OpenAI API to generate an image URL from it
def generate_image(description):
    # Use the Image.create method to generate an image from the description using DALL-E
    try: # Added a try-except block to handle any errors from the OpenAI API
        image = openai.Image.create(
            prompt=description,
            size="512x512", # Set the size of the image in pixels (width, height)
        )
        # Return the URL of the image
        return image.data[0].url # Get the URL from the first element of the data list
    except openai.error.OpenAIError as e: # Added an exception handler for OpenAIError, which is raised when there is an error in the OpenAI API request or response
        print(f"An error occurred while generating an image from OpenAI: {e}")
        return None

def create_image(image_url, product_id):
    # Use the requests library to download the image data from the URL
    response = requests.get(image_url)
    if response.status_code == 200: # Check if the response is successful (200 OK)
        # Use the Images.create method to create an image on BigCommerce using the product ID and the image data
        
        try: # Added a try-except block to handle any errors from the BigCommerce API
            # Create a payload dictionary with the image file object
            payload = {
                'image_file': ('image.jpg', response.content, 'image/jpeg') # Set this to a tuple of (filename, file content, file type)
            }
            
            # Create a header dictionary with the authorization
            headers = {
                'X-Auth-Client': config["bigcommerce_client_id"],
                'X-Auth-Token': config["bigcommerce_api_key"],
            }
            
            # Send a POST request to the v3 catalog API endpoint for creating an image
            response = requests.post(f'https://api.bigcommerce.com/stores/{config["bigcommerce_store_hash"]}/v3/catalog/products/{product_id}/images', files=payload, headers=headers)
            
            # Check the response status code and print the result
            if response.status_code == 200: # The request was successful
                print(f"Image created successfully!")
            else: # The request failed
                print(f"An error occurred while creating an image on BigCommerce: {response.status_code} {response.text}")
        except bigcommerce.exception.ClientRequestException as e: # Added an exception handler for ClientRequestException, which is raised when there is an error in the request parameters or headers
            print(f"An error occurred while creating an image on BigCommerce: {e}")
            return None
    else: # The response is not successful, so return None
        print(f"An error occurred while downloading the image from OpenAI: {response.status_code}")
        return None


# Write a main function that initializes the application and prompts the user for inputs and calls the functions to generate and create products
def main():
    # Initialize the application and read the configuration file
    print("Welcome to the BigCommerce Product Generator!")
    print("This application will help you create products on your BigCommerce store using the ChatGPT and DALL-E APIs.")
    
    # Prompt the user for a product category name and other inputs
    category = input("Please enter a product category name: ")
    inputs = input("Please enter any other inputs you want to use for generating products (separated by commas): ")
    # Prompt the user for the number of products to generate and create
    num_products = int(input("Please enter the number of products you want to generate and create: "))

    # Loop through the number of products and call the functions to generate and create products
    for i in range(num_products):
        print(f"Generating product {i+1}...")
        # Generate a product using ChatGPT
        product_data = generate_product(category, inputs)
        if product_data: # Added a check for None product data to avoid passing it to the next function
            # Create a product using BigCommerce
            product = create_product(product_data, category)
            if product: # Added a check for None product object to avoid printing invalid data
                # Print the result
                print(f"Product {i+1} created successfully!")
                print(f"Product ID: {product.id}")
                print(f"Product Name: {product.name}")
                print(f"Product Description: {product.description}")
                print(f"Product Price: {product.price}")
                print(f"Product Weight: {product.weight}")
                # Generate an image URL using DALL-E
                image_url = generate_image(product.description)
                if image_url: # Added a check for None image URL to avoid passing it to the next function
                    # Create an image on BigCommerce using the URL
                    image = create_image(image_url, product.id)
                    if image: # Added a check for None image object to avoid printing invalid data
                        # Print the result
                        print(f"Image created successfully!")
                       
                    
                else:
                    print(f"Image generation failed!")
            else:
                print(f"Product {i+1} creation failed!")
        else:
            print(f"Product {i+1} generation failed!")
        print("Thank you for using the BigCommerce Product Generator!")
main()
