from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import base64
import requests
import os
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
api_key = os.getenv("API_KEY")

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Function to process image and extract Date of Birth
def process_image(image):
    image_path = 'temp_image.png'
    image.save(image_path, 'PNG')
    base64_image = encode_image(image_path)
    
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
                        "text": "Extract only Date of Birth."
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

@app.route('/extract_dob', methods=['POST'])
def extract_dob():
    if 'file' in request.files:
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        file_type = file.content_type
        temp_dir = 'temp'

        try:
            if file_type == 'application/pdf':
                # Create temp directory if it doesn't exist
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir)

                # Save uploaded PDF to the temp directory
                temp_pdf_path = os.path.join(temp_dir, file.filename)
                file.save(temp_pdf_path)
                
                # Extract images from the uploaded PDF using PyMuPDF
                doc = fitz.open(temp_pdf_path)
                results = []

                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap()
                    image_path = os.path.join(temp_dir, f'page_{page_num + 1}.png')
                    pix.save(image_path)
                    
                    image = Image.open(image_path)
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
        finally:
            # Clean up temp files
            if os.path.exists(temp_dir):
                for file in os.listdir(temp_dir):
                    os.remove(os.path.join(temp_dir, file))
                os.rmdir(temp_dir)

    elif 'image' in request.json:
        data = request.get_json()
        image_base64 = data['image']
        image_data = base64.b64decode(image_base64)
        
        image_path = 'temp_image.png'
        with open(image_path, 'wb') as image_file:
            image_file.write(image_data)
        
        image = Image.open(image_path)
        extracted_text = process_image(image)
        
        return jsonify({"extracted_text": extracted_text}), 200

    else:
        return jsonify({"error": "No file part or image data"}), 400

if __name__ == '__main__':
    app.run(debug=True)
