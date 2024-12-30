from flask import Flask, request, jsonify
import os
from PyPDF2 import PdfReader
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from flask_cors import CORS

# Initialize the Flask app
app = Flask(__name__)
allowed_origins = [
    "https://file-ectractor-client.vercel.app",
    "http://localhost:5174",  # For local testing
    "http://localhost:5173",
]

CORS(app, origins=allowed_origins)

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def extract_images_from_pdf(pdf_path, output_dir):
    """Extract images from a PDF file and save them to the output directory."""
    images = []
    with fitz.open(pdf_path) as pdf:
        for page_number in range(len(pdf)):
            page = pdf[page_number]
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = pdf.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                image_path = os.path.join(output_dir, f"page{page_number + 1}_img{img_index + 1}.{image_ext}")
                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)
                images.append(image_path)
    return images

def extract_text_from_image(image_path):
    """Extract text from an image file using Tesseract OCR."""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        return f"Error processing image: {str(e)}"

@app.route("/extract", methods=["POST"])
def extract():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    try:
        # Ensure the temp directory exists
        temp_dir = "./temp"
        os.makedirs(temp_dir, exist_ok=True)

        # Save the file temporarily
        file_path = os.path.join(temp_dir, file.filename)
        file.save(file_path)

        # Check file type and process accordingly
        if file.filename.lower().endswith('.pdf'):
            # Extract text from the PDF
            text = extract_text_from_pdf(file_path)

            # Extract images from the PDF
            images_dir = os.path.join(temp_dir, "images")
            os.makedirs(images_dir, exist_ok=True)
            images = extract_images_from_pdf(file_path, images_dir)
        elif file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            # Extract text from the image
            text = extract_text_from_image(file_path)
            images = [file_path]  # Return the uploaded image itself
        else:
            return jsonify({"error": "Unsupported file type. Please upload a PDF or an image file."}), 400

        # Optionally delete the temporary file after processing
        os.remove(file_path)

        return jsonify({
            "content": text,
            "images": images  # Paths to the extracted images
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

