import requests

def reply_to_whatsapp(phone_number_id, access_token, recipient, message):
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "text",
        "text": {"body": message}
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

reply_to_whatsapp(
    "YOUR_PHONE_NUMBER_ID",
    "YOUR_ACCESS_TOKEN",
    "RECIPIENT_NUMBER",
    "Hello, this is an automated reply."
)