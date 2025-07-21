import base64
import os
import fitz  # PyMuPDF
from PIL import Image
from datetime import datetime
import requests
from typing import Optional, List
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
import json
from statistics import mean, median, mode, StatisticsError
from collections import Counter

# 🔐 Load environment variables from .env
load_dotenv()

# 📦 Receipt Item Model
class ReceiptItem(BaseModel):
    name: str
    quantity: Optional[float] = 1
    unit: Optional[str] = None
    price: Optional[float] = 0.0
    total: Optional[float] = None

# 🧾 Full Receipt Schema
class ReceiptData(BaseModel):
    vendor: str
    date: datetime
    amount: float
    category: Optional[str] = "Unknown"
    bill_number: Optional[str] = None
    order_id: Optional[str] = None
    payment_method: Optional[str] = None
    payment_status: Optional[str] = "Paid"
    tax: Optional[float] = None
    discount: Optional[float] = None
    service_charge: Optional[float] = None
    tip: Optional[float] = None
    currency: Optional[str] = "INR"
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    items: Optional[List[ReceiptItem]] = None
    remarks: Optional[str] = None
    location: Optional[str] = None
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None

# 🖼️ Encode image/pdf to base64
def encode_file_base64(file_path):
    ext = file_path.lower().split('.')[-1]
    if ext in ['jpg', 'jpeg', 'png', 'webp', 'tiff']:
        with open(file_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8'), "image/png"
    elif ext == 'pdf':
        doc = fitz.open(file_path)
        first_page = doc.load_page(0)
        pix = first_page.get_pixmap()
        img_bytes = pix.tobytes("png")
        return base64.b64encode(img_bytes).decode("utf-8"), "image/png"
    else:
        raise ValueError("Unsupported file type")

# 🔗 Gemini API Call
def call_gemini_llm(base64_data, mime_type):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise Exception("❌ GEMINI_API_KEY not found in .env")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    prompt = {
        "parts": [
            {
                "text": """
You are an intelligent receipt parser.

From the provided image, extract all receipt fields and return strictly in this JSON format:

{
  "vendor": "string",
  "date": "YYYY-MM-DD",
  "amount": float,
  "category": "string",
  "bill_number": "string or null",
  "order_id": "string or null",
  "payment_method": "string or null",
  "payment_status": "Paid",
  "tax": float or null,
  "discount": float or null,
  "service_charge": float or null,
  "tip": float or null,
  "currency": "string (e.g., INR, USD, EUR, etc.) — must be detected from the receipt",
  "customer_name": "string or null",
  "customer_email": "string or null",
  "customer_phone": "string or null",
  "items": [
    {
      "name": "string",
      "quantity": float or null,
      "unit": "string or null",
      "price": float or null,
      "total": float or null
    }
  ] or null,
  "remarks": "string or null",
  "location": "string or null",
  "billing_address": "string or null",
  "shipping_address": "string or null"
}

Return only valid JSON. No explanation or markdown.
"""
            },
            {
                "inlineData": {
                    "mimeType": mime_type,
                    "data": base64_data
                }
            }
        ]
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, json={"contents": [prompt]})
    response_json = response.json()

    try:
        reply = response_json["candidates"][0]["content"]["parts"][0]["text"]
        print("🧠 Gemini Raw Output:", reply)
        return reply
    except Exception as e:
        print("❌ Gemini Error:", response_json)
        raise e

# 🧠 Main Parsing Function
def parse_receipt(file_path):
    try:
        base64_data, mime_type = encode_file_base64(file_path)
        raw_response = call_gemini_llm(base64_data, mime_type)

        if raw_response.strip().startswith("```"):
            raw_response = raw_response.strip().strip("```json").strip("```").strip()

        parsed_json = json.loads(raw_response)
        receipt = ReceiptData(**parsed_json)

        return {
            "vendor": receipt.vendor,
            "date": receipt.date.date(),
            "amount": receipt.amount,
            "category": receipt.category
        }

    except (ValidationError, json.JSONDecodeError, Exception) as e:
        return {
            "vendor": "ParseError",
            "date": datetime.now().date(),
            "amount": 0.0,
            "category": "Unknown",
            "error": str(e)
        }

# 📊 Compute Aggregates
def compute_stats(receipts):
    if not receipts:
        return {
            "total": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "mode": "N/A",
            "vendor_frequency": {}
        }

    amounts = [r[3] for r in receipts if isinstance(r[3], (int, float))]
    vendors = [r[1] for r in receipts]

    try:
        mode_val = mode(amounts)
    except StatisticsError:
        mode_val = "N/A"

    stats = {
        "total": round(sum(amounts), 2),
        "mean": round(mean(amounts), 2) if amounts else 0.0,
        "median": round(median(amounts), 2) if amounts else 0.0,
        "mode": round(mode_val, 2) if isinstance(mode_val, (int, float)) else "N/A",
        "vendor_frequency": dict(Counter(vendors))
    }

    return stats
