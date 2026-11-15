import re
import requests
import urllib.parse
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def normalize_phone_number(phone_number: str) -> str:
    """
    Standardizes any phone number into Meta WhatsApp format (e.g. 919876543210).
    Robustly handles:
    - 9876543210 -> 919876543210
    - +91 98765-43210 -> 919876543210
    - 09876543210 -> 919876543210
    - 919876543210 -> 919876543210
    - +91919876543210 -> 919876543210
    """
    if not phone_number:
        return ""
    clean = re.sub(r"\D", "", str(phone_number))

    # Strip repeated leading 91 prefixes if user mistakenly entered it multiple times
    while clean.startswith("91") and len(clean) > 12:
        clean = clean[2:]

    # Strip leading 0 if 11 digits (e.g. 09876543210)
    if len(clean) == 11 and clean.startswith("0"):
        clean = clean[1:]

    # Prefix 91 if standard 10 digit Indian number
    if len(clean) == 10:
        return "91" + clean

    return clean


def generate_whatsapp_link(phone_number: str, message: str) -> str:
    """
    Generates a WhatsApp click-to-chat URL (wa.me) with a prefilled message.
    """
    clean_phone = normalize_phone_number(phone_number)
    encoded_message = urllib.parse.quote(message)
    return f"https://api.whatsapp.com/send?phone={clean_phone}&text={encoded_message}"


def send_whatsapp_message(phone_number: str, message: str, gateway: str = "mock"):
    """
    Helper to send plain WhatsApp text message via an API gateway / webhook.
    """
    clean_phone = normalize_phone_number(phone_number)
    logger.info(f"Sending WhatsApp message to {clean_phone}: {message}")
    return {
        "sent": True,
        "recipient": clean_phone,
        "mode": gateway
    }


def send_whatsapp_template_message(recipient_number: str, submission_id: int):
    """
    Sends WhatsApp message using Meta Approved Template 'shreyas_admission'
    with Dynamic Button URL containing submission_id.
    """
    clean_phone = normalize_phone_number(recipient_number)

    phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')
    access_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '')

    if not phone_number_id or not access_token:
        logger.warning("WhatsApp credentials not set in .env")
        return {"success": False, "error": "WhatsApp credentials not set in .env"}

    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Payload matching your exact template: shreyas_admission
    # Dynamic button parameter: submission_id (e.g. "1")
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        "type": "template",
        "template": {
            "name": "shreyas_admission",
            "language": {
                "code": "en"
            },
            "components": [
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [
                        {
                            "type": "text",
                            "text": str(submission_id)
                        }
                    ]
                }
            ]
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        res_data = response.json()
        logger.info(f"WhatsApp Template response for {clean_phone}: {res_data}")

        if response.status_code == 200:
            return {"success": True, "data": res_data, "recipient": clean_phone}
        else:
            logger.error(f"WhatsApp Template message failed for {clean_phone}: {res_data}")
            return {"success": False, "error": res_data, "recipient": clean_phone}
    except Exception as e:
        logger.error(f"WhatsApp sending exception: {str(e)}")
        return {"success": False, "error": str(e), "recipient": clean_phone}
