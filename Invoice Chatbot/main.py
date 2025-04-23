from invoice_utils import process_bot_response
import google.generativeai as genai
import os

# Configure API key
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-pro')

def chat_with_bot(user_input):
    try:
        # Get response from the model
        response = model.generate_content(user_input)
        response_text = response.text
        
        # Process the response for invoice generation
        if "CONFIRMED!" in response_text:
            process_bot_response(response_text)
            
        return response_text
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    # Initialize chat
    chat = model.start_chat(history=[])
    
    # Send initial system prompt
    chat.send_message("""You're an Invoice Generator Bot. 

Start EVERY conversation by saying:
"I'll need some information from you to generate the invoice. Please provide:
- Your company name
- Your company address
- Your contact number
- Your email address
- Your preferred payment details (e.g., PayPal, bank details)

You can provide this information in any order, and I'll keep track of what's missing."

Track all provided information and use it in the JSON output. Never use placeholder values like "Customer Name" or "Customer Address". 

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
            "amount": "[actual amount as number]"
        }
    ],
    "due_date": "[actual due date]"
}

Always use the actual provided values, never placeholder text.""")

    print("Invoice Generator Bot: Hi! I'm here to help with invoices. I support Sales (SI), Purchases (PI), Debit Note (DN), and Credit Note (CN).")
    print("Pick one to start, or ask me about invoice uses and requirements!")

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() == 'quit':
            break

        response = chat.send_message(user_input)
        print("\nBot:", response.text)

        # Process response for invoice generation
        result = process_bot_response(response.text)
        if result:
            print(result)
            print("\nNote: Please check the location above to find your generated invoice PNG file.")

if __name__ == "__main__":
    main()