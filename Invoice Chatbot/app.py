import streamlit as st
import os
import re
import os
from datetime import datetime
from invoice_utils import process_bot_response
import google.generativeai as genai
import time
from PIL import Image

st.set_page_config(page_title="Invoice Generator", layout="wide")

# Initialize session state variables first
if "messages" not in st.session_state:
    st.session_state.messages = []
if "generated_files" not in st.session_state:
    st.session_state.generated_files = []
if "current_invoice" not in st.session_state:
    st.session_state.current_invoice = None
if "chat" not in st.session_state:
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel(
        "models/gemini-2.0-flash",
        generation_config=genai.types.GenerationConfig(temperature=0.3, max_output_tokens=500, top_p=0.9)
    )
    st.session_state.chat = model.start_chat(history=[])
    # Send initial welcome message
    welcome_message = """Hi! I'm your Invoice Generator Bot. I can help you create:
- Sales Invoices (SI)
- Purchase Invoices (PI)
- Debit Notes (DN)
- Credit Notes (CN)

Just pick one to start, or ask me about invoice requirements!"""
    st.session_state.messages.append({"role": "assistant", "content": welcome_message})
    
    # Send the configuration message to the bot
    st.session_state.chat.send_message("""You're an Invoice Generator Bot...""")
    st.session_state.chat.send_message("""You're an Invoice Generator Bot. 

Start the conversation by telling them what you need to generate the invoice:
"I'll need some information from you to generate the invoice. Please provide:
- Your company name
- Your company address
- Your contact number
- Your email address
- Your preferred payment details (e.g., PayPal, bank details)
"when filling in the invoice type make sure you either get sales invoice, purchase invoice, debit note, or credit note. if the user has not stated keep asking until you get one of these 4."
the user can provide this information in any order, and you  keep track of what's missing."

Track all provided information and use it in the JSON output. Never use placeholder values like "Customer Name" or "Customer Address". 
"when all requirements are met ask if there are any more modification ar we can proceed with the generation of the invoice"
When generating the CONFIRMED! JSON, use this format with the actual collected values:
CONFIRMED!
{
    "type": "[actual invoice type]",
    "company_info": {
        "name": "[actual company name provided]",
        "address": "[actual address provided]",
        "contact": "[actual contact provided]",
        "email": "[actual email provided]",
        "payment_method": "[actual payment details provided]"
    },
    "customer_name": "[actual customer name]",
    "recipient_address": "[actual recipient address]",
    "recipient_contact": "[actual recipient contact]",
    "items": [
        {
            "description": "[actual item description]",
            "quantity": "[actual quantity as number]",
            "amount": "[actual amount as number, this is the price per item only put price per item. calculate it if given total value]"
        }
    ],
    "due_date": "[actual due date]"
}
"if the user says override 123 the generate these values for yourself and give the confirmed message, its for testing"

Always use the actual provided values, never placeholder text.""")

# Update CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500&display=swap');
    
    @keyframes backgroundShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .header {
        text-align: center;
        font-size: 2.5em;
        font-weight: bold;
        padding: 20px;
        margin-bottom: 30px;
        background: linear-gradient(270deg, #ff6b6b, #4ecdc4, #45b7d1, #96c93d);
        background-size: 800% 800%;
        animation: backgroundShift 10s ease infinite;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Roboto', sans-serif;
    }
    .user-message {
        text-align: right;
        background-color: #808080;
        padding: 12px 20px;
        border-radius: 20px;
        margin: 5px 0;
        color: #FFFFFF;
        width: 35%;
        margin-left: auto;
    }
    .bot-message {
        width: 80%;
        margin: 10px auto;
        padding: 15px;
        font-family: 'Roboto', sans-serif;
        color: #FFFFFF;
        font-size: 16px;
        text-align: left;
    }
    .stTextInput {
        width: 60% !important;
        margin: 0 auto;
        position: relative;
    }
    
    .creator-text {
        text-align: center;
        color: #666666;
        font-size: 12px;
        margin-top: 10px;
        font-family: 'Roboto', sans-serif;
    }
    </style>
""", unsafe_allow_html=True)

# Add header before chat history
st.markdown('<div class="header">Let\'s Talk & Make Invoices!</div>', unsafe_allow_html=True)

# Display chat history
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f'<div class="user-message">{message["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bot-message">{message["content"]}</div>', unsafe_allow_html=True)

# Add invoice display section before chat input
if st.session_state.current_invoice and os.path.exists(st.session_state.current_invoice):
    st.markdown("""
        <style>
        .invoice-container {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 20px;
        }
        .invoice-display {
            width: 40%;
            margin-right: 20px;
        }
        .stImage {
            margin-bottom: 0 !important;
        }
        .stImage img {
            border-radius: 4px 4px 0 0 !important;
        }
        .stDownloadButton {
            width: 100% !important;
            margin-top: 0 !important;
        }
        .stDownloadButton button {
            width: 100% !important;
            background: linear-gradient(90deg, #4ecdc4, #45b7d1) !important;
            transition: all 0.3s ease !important;
            border-radius: 0 0 4px 4px !important;
        }
        .stDownloadButton button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
            background: linear-gradient(90deg, #45b7d1, #4ecdc4) !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="invoice-container">', unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    with col1:
        try:
            st.image(st.session_state.current_invoice, use_container_width=True)
            with open(st.session_state.current_invoice, "rb") as file:
                st.download_button(
                    label=f"📄 Download {os.path.splitext(st.session_state.current_invoice)[0]}",
                    data=file.read(),
                    file_name=st.session_state.current_invoice,
                    mime="image/png",
                    key="invoice_download"  # Added unique key
                )
        except Exception as e:
            st.error(f"Error displaying invoice: {str(e)}")
            print(f"Error: {str(e)}")
    st.markdown('</div>', unsafe_allow_html=True)

# Update the chat input section
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False
    
    if "input_key" not in st.session_state:
        st.session_state.input_key = 0
    
    user_input = st.text_input(
        label="Message Input",
        key=f"user_input_{st.session_state.input_key}",
        placeholder="Type your message here...",
        disabled=st.session_state.is_processing,
        label_visibility="collapsed"
    )
    
    if "last_message" not in st.session_state:
        st.session_state.last_message = ""
    
    if user_input and user_input != st.session_state.last_message and not st.session_state.is_processing:
        st.session_state.is_processing = True
        st.session_state.last_message = user_input
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Get bot response and process
        response = st.session_state.chat.send_message(user_input)
        response_text = response.text
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        
        # Process for invoice generation
        if "CONFIRMED!" in response_text:
            try:
                result, invoice_id = process_bot_response(response_text)
                if result:
                    filename = f"{invoice_id}.png"
                    print(f"Processing invoice: {filename}")
                    
                    # Add delay to ensure file is completely written
                    time.sleep(2)
                    
                    # Store the filename in session state for display after rerun
                    st.session_state.current_invoice = filename
                    st.session_state.input_key += 1
            except Exception as e:
                print(f"Error processing invoice: {str(e)}")
                st.error("Failed to generate invoice. Please try again.")
        
        st.session_state.is_processing = False
        st.rerun()

# Add creator credit here
st.markdown('<div class="creator-text">Created by Nokutenda K Denga | 12317891</div>', unsafe_allow_html=True)