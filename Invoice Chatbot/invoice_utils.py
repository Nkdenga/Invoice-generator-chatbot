import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import re
import time
import os
import json  # Add this at the top with other imports

# Configure Gemini API
API_KEY = os.getenv('GEMINI_API_KEY')  # Using environment variable
genai.configure(api_key=API_KEY)

# Single model with chat session
model = genai.GenerativeModel(
    "models/gemini-2.0-flash",  # Updated model name
    generation_config=genai.types.GenerationConfig(temperature=0.3, max_output_tokens=500, top_p=0.9)
)

# Authorization settings
AUTH_KEY = "INV2025"
MAX_ATTEMPTS = 3
LOCKOUT_SECONDS = 300

# State variables
invoice_counters = {
    "Sales Invoice": 0,
    "Purchases Invoice": 0,
    "Debit Note": 0,
    "Credit Note": 0
}
lockout_start = None
attempts_left = MAX_ATTEMPTS

# Invoice types with prefixes
# Add at the top of the file, after imports
invoice_types = {
    "Sales Invoice": {"prefix": "SI"},
    "Purchase Invoice": {"prefix": "PI"},
    "Credit Note": {"prefix": "CN"},
    "Debit Note": {"prefix": "DN"}
}

invoice_counters = {
    "Sales Invoice": 0,
    "Purchase Invoice": 0,
    "Credit Note": 0,
    "Debit Note": 0
}
lockout_start = None
attempts_left = MAX_ATTEMPTS

# Invoice types with prefixes
# Remove the duplicate definitions and keep only this one
invoice_types = {
    "Sales Invoice": {"prefix": "SI", "static_fields": ["customer_name", "recipient_address", "recipient_contact"], "item_fields": ["product_name", "quantity", "unit_price"]},
    "Purchases Invoice": {"prefix": "PI", "static_fields": ["supplier_name", "supplier_address", "supplier_contact"], "item_fields": ["product_name", "quantity", "unit_price"]},
    "Debit Note": {"prefix": "DN", "static_fields": ["supplier_name", "supplier_address", "supplier_contact"], "item_fields": ["description", "quantity", "amount"]},
    "Credit Note": {"prefix": "CN", "static_fields": ["customer_name", "recipient_address", "recipient_contact"], "item_fields": ["description", "quantity", "amount"]}
}

# Keep only one instance of invoice_counters
invoice_counters = {
    "Sales Invoice": 0,
    "Purchases Invoice": 0,
    "Debit Note": 0,
    "Credit Note": 0
}

def generate_invoice_id(invoice_type):
    if invoice_type in invoice_types:
        invoice_counters[invoice_type] += 1
        return f"{invoice_types[invoice_type]['prefix']}-{str(invoice_counters[invoice_type]).zfill(4)}"
    print(f"Warning: Unknown invoice type '{invoice_type}'")  # Debug print
    return "UNKNOWN"  # Return a default value instead of None

def calculate_totals(invoice_data, invoice_type):
    subtotal = 0.0
    for item in invoice_data.get("items", []):
        if "product_name" in item:
            qty = float(item["quantity"])
            price = float(item["unit_price"])
        elif "description" in item:
            qty = float(item["quantity"])
            price = float(item["amount"])
        subtotal += qty * price

    shipping = 0.0
    if invoice_type in ["Sales Invoice", "Purchases Invoice"]:
        shipping = subtotal * 0.05

    total = subtotal + shipping

    invoice_data["subtotal"] = f"{subtotal:.2f}"
    if shipping > 0:
        invoice_data["shipping"] = f"{shipping:.2f}"
    invoice_data["total"] = f"{total:.2f}"

    return invoice_data

def extract_json_data(text):
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != -1:
            json_str = text[start:end]
            print(f"Extracted JSON data: {json_str}")  # Debug print
            return eval(json_str)
    except Exception as e:
        print(f"Error extracting JSON: {str(e)}")  # Debug print
        return None

def create_invoice_png(invoice_data, invoice_type, invoice_id):
    img = Image.new('RGB', (800, 800), 'white')
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    # Company Header (0-100px)
    draw.rectangle([(0, 0), (800, 100)], fill='#E6F0FA')
    company_info = invoice_data.get('company_info', {})
    draw.text((10, 10), company_info.get('name', ''), font=font, fill='black')
    draw.text((10, 30), company_info.get('address', ''), font=font, fill='black')
    draw.text((10, 50), f"Contact: {company_info.get('contact', '')}", font=font, fill='black')
    draw.text((10, 70), f"Email: {company_info.get('email', '')}", font=font, fill='black')

    # Invoice Details (top right)
    draw.text((600, 10), invoice_type, font=font, fill='black')
    draw.text((600, 30), f"INV-{invoice_id}", font=font, fill='black')
    draw.text((600, 50), "Date: April 06, 2025", font=font, fill='black')

    # Customer/Supplier Info (120-190px)
    if invoice_type in ["Sales Invoice", "Credit Note"]:
        draw.text((10, 120), "Bill To:", font=font, fill='black')
    else:
        draw.text((10, 120), "Bill From:", font=font, fill='black')
    draw.text((10, 140), invoice_data.get('customer_name', ''), font=font, fill='black')
    draw.text((10, 160), invoice_data.get('recipient_address', ''), font=font, fill='black')
    draw.text((10, 180), invoice_data.get('recipient_contact', ''), font=font, fill='black')

    # Items Table (210-290px)
    draw.rectangle([(10, 210), (790, 290)], outline='#D3D3D3')
    draw.line([(10, 230), (790, 230)], fill='#D3D3D3')
    
    # Table Headers
    draw.text((20, 215), "Description", font=font, fill='black')
    draw.text((300, 215), "Qty", font=font, fill='black')
    draw.text((400, 215), "Amount", font=font, fill='black')
    draw.text((600, 215), "Total", font=font, fill='black')

    # Items List
    y = 245
    total = 0
    for item in invoice_data.get("items", []):
        name = item.get("description", "")
        qty = float(item.get("quantity", "0"))
        # Handle both string and numeric price values
        price = item.get("amount", "0")
        if isinstance(price, str):
            price = float(price.replace("$", ""))
        else:
            price = float(price)
        item_total = qty * price
        total += item_total
        
        draw.text((20, y), str(name), font=font, fill='black')
        draw.text((300, y), str(int(qty)), font=font, fill='black')
        draw.text((400, y), f"${price:.2f}", font=font, fill='black')
        draw.text((600, y), f"${item_total:.2f}", font=font, fill='black')
        y += 30

    # Totals Section
    draw.rectangle([(500, y + 20), (790, y + 60)], fill='#E6FFE6')
    draw.text((510, y + 30), f"Total Amount: ${total:.2f}", font=font, fill='black')

    # Footer with dynamic payment info
    draw.text((10, y + 90), f"Due: {invoice_data.get('due_date', '')}", font=font, fill='black')
    draw.text((10, y + 110), f"Payment Method: {company_info.get('payment_method', '')}", font=font, fill='black')

    img.save(f"{invoice_id}.png", "PNG")
    return f"{invoice_id}.png"


# Update the invoice counters at the top of the file
invoice_counters = {
    'SI': 0,  # Sales Invoice counter
    'PI': 0,  # Purchase Invoice counter
    'DN': 0,  # Debit Note counter
    'CN': 0   # Credit Note counter
}

def process_bot_response(response_text):
    try:
        if "CONFIRMED!" in response_text:
            # Clean and parse the JSON string
            json_str = response_text.split("CONFIRMED!")[1].strip()
            
            # Remove ```json``` tags if present
            if json_str.startswith('```json'):
                json_str = json_str.replace('```json', '').replace('```', '').strip()
            
            print("1. Cleaned JSON string:", json_str)
            
            # Replace single quotes with double quotes for valid JSON
            json_str = json_str.replace("'", '"')
            print("2. Processing JSON data...")
            
            # Parse JSON and verify data
            data = json.loads(json_str)
            print("3. Parsed data:", data)
            
            # Get invoice type and preserve original case
            original_type = data.get('type', '')
            invoice_type = original_type.lower()
            
            # Generate specific invoice ID based on type
            if "sales invoice" in invoice_type:
                invoice_counters['SI'] += 1
                invoice_id = f"SI-{invoice_counters['SI']}"
            elif "purchase invoice" in invoice_type:
                invoice_counters['PI'] += 1
                invoice_id = f"PI-{invoice_counters['PI']}"
            elif "debit note" in invoice_type:
                invoice_counters['DN'] += 1
                invoice_id = f"DN-{invoice_counters['DN']}"
            elif "credit note" in invoice_type:
                invoice_counters['CN'] += 1
                invoice_id = f"CN-{invoice_counters['CN']}"
            else:
                print(f"Error: Unsupported invoice type: {invoice_type}")
                return False, None
            
            print(f"5. Generated ID: {invoice_id}")
            
            # Create invoice with the new ID format
            filename = f"{invoice_id}.png"
            create_invoice_png(data, original_type, invoice_id)
            
            if os.path.exists(filename):
                print(f"6. Invoice created successfully: {filename}")
                return True, invoice_id
            else:
                print("Error: Failed to create invoice file")
                return False, None
            
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {str(e)}")
        print(f"Problematic JSON string: {json_str}")
        return False
    except Exception as e:
        print(f"Error processing invoice: {str(e)}")
        return False
