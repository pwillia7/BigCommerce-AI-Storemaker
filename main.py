# Import the required packages and libraries
import openai
import bigcommerce
import requests
import logging
import re

# Create a configuration file that stores the API keys and store hash
config = {
    "openai_api_key": "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",
    "bigcommerce_api_key": "kb8erl2xnpttb6n9xchcnarqz3dahdy",
    "bigcommerce_store_hash": "eq6sthvjcq",
    "bigcommerce_client_id": "9ykv7ebuult3u9561xfsgcwzn2qrxa3"
}

# Connect to the BigCommerce API using OAuth
api = bigcommerce.api.BigcommerceApi(
    client_id=config["bigcommerce_client_id"],
    store_hash=config["bigcommerce_store_hash"],
    access_token=config["bigcommerce_api_key"]
)

# Connect to the OpenAI API using your secret key
openai.api_key = config["openai_api_key"]

# Set up a logger to log the errors and results to a file
logging.basicConfig(filename='product_generator.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Write a function that takes a product category name and other inputs from the user and uses the Completion API to generate a product name, description, price, and weight
def generate_product(category, inputs):
    # Use the Completion endpoint with the gpt-4 model to get natural language responses from ChatGPT
    query = f"Generate a product name, description, price, and weight for a {category} product based on these inputs: {inputs}\n\nExample output:\nProduct name: Alpine Explorer Men's Outdoor Jacket\nDescription: Crafted for those who love the great outdoors, the Alpine Explorer Men's Outdoor Jacket is a stylish fusion of form and function. Made with a blend of high-performance materials, it ensures optimal warmth and water-resistance while providing full-range mobility.\nPrice: 249.99\nWeight: 2.5\n\nPlease only output in this format."
    try:
        # Use the Completion endpoint with some parameters to control the creativity and diversity of the responses
        response = openai.Completion.create(
            prompt=query,
            engine="gpt-4",
            max_tokens=100,
            temperature=0.8,
            top_p=0.9,
            frequency_penalty=0.1,
            presence_penalty=0.1,
            logprobs=10 # Get the probabilities of the top 10 tokens for each position
        )
    except openai.error.OpenAIError as e:
        logging.error(f"An error occurred while using the OpenAI API: {e}")
        return None
    # Parse the response and return a dictionary with the product data
    product_data = {}
    # Check if the response object has the choices attribute
    if hasattr(response, "choices"):
        # Get the list of choices from the response
        choices = response.choices
        # Filter out any choices that have an incomplete or invalid finish reason or low log probability
        valid_choices = [choice for choice in choices if choice.finish_reason in ["stop", "length"] and choice.logprobs.token_logprobs[-1] > -3]
        # Choose one of the valid choices, either by using the first one or by using some criteria
        chosen_choice = valid_choices[0] # This is a simple example, you can use other criteria to choose the best choice
        # Get the text from the chosen choice
        text = chosen_choice.text
        # Check if the text has the expected format and length of 4 lines
        if len(text.split("\n")) == 4 and all(line.startswith(("Product name", "Description", "Price", "Weight")) for line in text.split("\n")):
            # Extract the product data from each line by using regular expressions to match the fields and values
            product_data["name"] = re.search(r"Product name: (.*)", text).group(1).strip()
            product_data["description"] = re.search(r"Description: (.*)", text).group(1).strip()
            try:
                product_data["price"] = float(re.search(r"Price: (.*)", text).group(1).strip())
            except ValueError as e:
                logging.error(f"An error occurred while parsing the price: {e}")
                return None
            try:
                product_data["weight"] = float(re.search(r"Weight: (.*)", text).group(1).strip())
            except ValueError as e:
                logging.error(f"An error occurred while parsing the weight: {e}")
                return None
            # Log the product data to the file
            logging.info(f"Product data generated successfully: {product_data}")
            return product_data
        else:
            # The text does not have the expected format or length, so log the error and return None
            logging.error(f"The response from the OpenAI API was not valid: {text}")
            return None
    else:
        # The response object does not have the choices attribute, so log the error and return None
        logging.error(f"The response from the OpenAI API was empty or invalid: {response}")
        return None

# Write a function that takes a category name as an input and returns the category ID as an output
def get_or_create_category(category):
    # Create a dictionary to store the category names and IDs as key-value pairs
    category_dict = {}
    # Get a list of all the categories and their IDs using the BigCommerce API
    categories = api.Categories.all()
    # Loop through the categories and add them to the dictionary
    for cat in categories:
        category_dict[cat.name] = cat.id
    # Look up the category name in the dictionary and return the ID if found
    if category in category_dict:
        return category_dict[category]
    # If not found, create a new category using the BigCommerce API and return the new ID
    else:
        # Validate the category name before creating it
        if category: # Check if the name is not empty or null
            if len(category) <= 50: # Check if the name is not too long
                if re.match(r"^[a-zA-Z0-9\s_-]+$", category): # Check if the name contains only alphanumeric characters, spaces, underscores, and dashes
                    try: # Added a try-except block to handle any errors from the BigCommerce API
                        new_category = api.Categories.create(name=category)
                        # Log the creation of a new category to the file
                        logging.info(f"New category created successfully: {new_category.name} ({new_category.id})")
                        return new_category.id
                    except bigcommerce.exception.ClientRequestException as e: # Added an exception handler for ClientRequestException, which is raised when there is an error in the request parameters or headers
                        logging.error(f"An error occurred while creating a new category on BigCommerce: {e}")
                        return None
                else:
                    # The name contains invalid or prohibited characters, so log the error and return None
                    logging.error(f"The category name is not valid: {category}")
                    return None
            else:
                # The name is too long, so log the error and return None
                logging.error(f"The category name is too long: {category}")
                return None
        else:
            # The name is empty or null, so log the error and return None
            logging.error(f"The category name is empty or null: {category}")
            return None

# Write a function that takes the product data generated by ChatGPT and uses the BigCommerce API to create a product on your BigCommerce store
# Write a function that takes the product data generated by ChatGPT and uses the BigCommerce API to create a product on your BigCommerce store
def create_product(product_data, category):
    # Validate the product data before creating it
    if product_data: # Check if the product data is not empty or null
        if all(product_data.values()): # Check if all the values in the product data are not empty or null
            if isinstance(product_data["name"], str) and isinstance(product_data["description"], str): # Check if the name and description are strings
                if isinstance(product_data["price"], float) and isinstance(product_data["weight"], float): # Check if the price and weight are floats
                    if 0 <= product_data["price"] <= 10000 and 0 <= product_data["weight"] <= 1000: # Check if the price and weight are within reasonable ranges
                    
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
                            # Log the creation of a new product to the file
                            logging.info(f"New product created successfully: {product.name} ({product.id})")
                            # Return the product object
                            return product
                        except bigcommerce.exception.ClientRequestException as e: # Added an exception handler for ClientRequestException, which is raised when there is an error in the request parameters or headers
                            logging.error(f"An error occurred while creating a new product on BigCommerce: {e}")
                            return None
                    else:
                        # The price or weight are out of reasonable ranges, so log the error and return None
                        logging.error(f"The product price or weight are not valid: {product_data['price']}, {product_data['weight']}")
                        return None
                else:
                    # The price or weight are not floats, so log the error and return None
                    logging.error(f"The product price or weight are not floats: {product_data['price']}, {product_data['weight']}")
                    return None
            else:
                # The name or description are not strings, so log the error and return None
                logging.error(f"The product name or description are not strings: {product_data['name']}, {product_data['description']}")
                return None
        else:
            # Some values in the product data are empty or null, so log the error and return None
            logging.error(f"Some values in the product data are empty or null: {product_data}")
            return None
    else:
        # The product data is empty or null, so log the error and return None
        logging.error(f"The product data is empty or null: {product_data}")
        return None

# Write a function that takes a product description and uses the ImageCompletion API to generate an image URL from it
def generate_image(description):
    # Use the ImageCompletion endpoint to generate an image from the description using DALL-E
    try: # Added a try-except block to handle any errors from the OpenAI API
        response = openai.ImageCompletion.create(
            prompt=description,
            engine="dall-e",
            max_tokens=256,
            temperature=0.8,
            top_p=0.9,
            frequency_penalty=0.1,
            presence_penalty=0.1,
            size="1024x1024", # Set the size of the image in pixels (width, height)
            logprobs=10 # Get the probabilities of the top 10 pixels for each position
        )
    except openai.error.OpenAIError as e: # Added an exception handler for OpenAIError, which is raised when there is an error in the OpenAI API request or response
        logging.error(f"An error occurred while generating an image from OpenAI: {e}")
        return None
    # Parse the response and return a dictionary with the image URL and probability
    image_data = {}
    # Check if the response object has the choices attribute
    if hasattr(response, "choices"):
        # Get the list of choices from the response
        choices = response.choices
        # Filter out any choices that have an incomplete or invalid finish reason or low log probability
        valid_choices = [choice for choice in choices if choice.finish_reason in ["stop", "length"] and choice.logprobs.pixel_logprobs[-1] > -3]
        # Choose one of the valid choices, either by using the first one or by using some criteria
        chosen_choice = valid_choices[0] # This is a simple example, you can use other criteria to choose the best choice
        # Get the URL and probability from the chosen choice
        image_data["url"] = chosen_choice.data[0].url # Get the URL from the first element of the data list
        image_data["probability"] = chosen_choice.logprobs.pixel_logprobs[-1] # Get the probability from the last element of the pixel_logprobs list
        # Log the image data to the file
        logging.info(f"Image data generated successfully: {image_data}")
        return image_data
    else:
        # The response object does not have the choices attribute, so log the error and return None
        logging.error(f"The response from the OpenAI API was empty or invalid: {response}")
        return None

def create_image(image_data, product_id):
    # Validate the image data before creating it
    if image_data: # Check if the image data is not empty or null
        if all(image_data.values()): # Check if all the values in the image data are not empty or null
            if isinstance(image_data["url"], str) and isinstance(image_data["probability"], float): # Check if the URL and probability are strings and floats respectively
                if 0 <= image_data["probability"] <= 1: # Check if the probability is within the range of 0 to 1
                    # Use the requests library to download the image data from the URL
                    response = requests.get(image_data["url"])
                    if response.status_code == 200: # Check if the response is successful (200 OK)
                        # Use the v3 catalog API to create an image on BigCommerce using the product ID and the image data
                        
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
                            
                            # Check the response status code and return a dictionary with the image ID and URL
                            if response.status_code == 200: # The request was successful
                                image_data = response.json()["data"]
                                image_id = image_data["id"]
                                image_url = image_data["url_standard"]
                                # Log the creation of a new image to the file
                                logging.info(f"New image created successfully: {image_id} ({image_url})")
                                return {"id": image_id, "url": image_url}
                            else: # The request failed
                                logging.error(f"An error occurred while creating an image on BigCommerce: {response.status_code} {response.text}")
                                return None
                        except bigcommerce.exception.ClientRequestException as e: # Added an exception handler for ClientRequestException, which is raised when there is an error in the request parameters or headers
                            logging.error(f"An error occurred while creating an image on BigCommerce: {e}")
                            return None
                    else: # The response is not successful, so log the error and return None
                        logging.error(f"An error occurred while downloading the image from OpenAI: {response.status_code}")
                        return None
                else:
                    # The probability is out of range, so log the error and return None
                    logging.error(f"The image probability is not valid: {image_data['probability']}")
                    return None
            else:
                # The URL or probability are not strings or floats, so log the error and return None
                logging.error(f"The image URL or probability are not valid: {image_data['url']}, {image_data['probability']}")
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
                image_data = generate_image(product.description)
                if image_data: # Added a check for None image data to avoid passing it to the next function
                    # Create an image on BigCommerce using the image data
                    image = create_image(image_data, product.id)
                    if image: # Added a check for None image object to avoid printing invalid data
                        # Print the result
                        print(f"Image created successfully!")
                        print(f"Image ID: {image['id']}")
                        print(f"Image URL: {image['url']}")
                    else:
                        print(f"Image creation failed!")
                else:
                    print(f"Image generation failed!")
            else:
                print(f"Product {i+1} creation failed!")
        else:
            print(f"Product {i+1} generation failed!")
    print("Thank you for using the BigCommerce Product Generator!")

# Call the main function to run the script
if __name__ == "__main__":
    main()


