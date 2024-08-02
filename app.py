from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import base64
import requests
import os
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
api_key = os.getenv("API_KEY")

# Function to encode the image
def encode_image(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# Function to process image and extract Date of Birth
def process_image(image):
    base64_image = encode_image(image)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract only Date of Birth. do not give any extra detail just reply date in given format dd/mm/yy"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    }
    
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return response.json()['choices'][0]['message']['content']


@app.route("/", methods=["GET", "POST"] )
def home():
    return "Welcome to homepage"


@app.route('/extract_dob', methods=["GET", 'POST'])
def extract_dob():
    if 'file' in request.files:
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        file_type = file.content_type

        try:
            if file_type == 'application/pdf':
                # Extract images from the uploaded PDF using PyMuPDF
                doc = fitz.open("pdf", file.read())
                results = []

                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap()
                    
                    image = Image.open(BytesIO(pix.tobytes()))
                    extracted_text = process_image(image)
                    results.append({"page": page_num + 1, "text": extracted_text})

                return jsonify({"extracted_texts": results}), 200

            elif file_type in ['image/png', 'image/jpeg']:
                image = Image.open(file.stream)
                extracted_text = process_image(image)
                
                return jsonify({"extracted_text": extracted_text}), 200
            
            else:
                return jsonify({"error": "Unsupported file type"}), 400
        except Exception as e:
            print(f"Error: {e}")
            return jsonify({"error": str(e)}), 500

    elif 'image' in request.json:
        data = request.get_json()
        image_base64 = data['image']
        image_data = base64.b64decode(image_base64)
        
        image = Image.open(BytesIO(image_data))
        extracted_text = process_image(image)
        response = {"response":extracted_text}
        
        return jsonify({"extracted_text": response}), 200

    else:
        return jsonify({"error": "No file part or image data"}), 400

if __name__ == '__main__':
    app.run(debug=True)
