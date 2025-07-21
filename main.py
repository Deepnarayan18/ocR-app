from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from parser import parse_receipt, compute_stats
from database import execute_query
import plotly.express as px
import os
import shutil
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
def show_receipts(request: Request):
    try:
        receipts = execute_query(" SELECT id, vendor, date, amount, category, currency FROM receipts1 ORDER BY date DESC")
        stats = compute_stats(receipts)
    except Exception as e:
        print("⚠️ Error:", e)
        receipts = []
        stats = {}

    return templates.TemplateResponse("index.html", {
        "request": request,
        "receipts": receipts,
        "stats": stats
    })

@app.post("/upload")
async def upload_receipt(request: Request, file: UploadFile = File(...)):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        print(f"📁 Saved: {file_path}")
        parsed = parse_receipt(file_path)
        print(f"🧠 Parsed: {parsed}")

        if parsed.get("vendor") == "ParseError":
            raise Exception(parsed.get("error"))

        insert_query = """
            INSERT INTO receipts1 (
                vendor, date, amount, category, bill_number, order_id,
                payment_method, payment_status, tax, discount,
                service_charge, tip, currency, customer_name,
                customer_email, customer_phone, remarks, location,
                billing_address, shipping_address
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            parsed.get("vendor"),
            parsed.get("date"),
            parsed.get("amount"),
            parsed.get("category"),
            parsed.get("bill_number"),
            parsed.get("order_id"),
            parsed.get("payment_method"),
            parsed.get("payment_status"),
            parsed.get("tax"),
            parsed.get("discount"),
            parsed.get("service_charge"),
            parsed.get("tip"),
            parsed.get("currency"),
            parsed.get("customer_name"),
            parsed.get("customer_email"),
            parsed.get("customer_phone"),
            parsed.get("remarks"),
            parsed.get("location"),
            parsed.get("billing_address"),
            parsed.get("shipping_address")
        )

        # Insert receipt and get ID
        receipt_id = execute_query(insert_query, params, fetch=False, return_last_id=True)

        # Insert items
        items = parsed.get("items")
        if items and isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    item_query = """
                        INSERT INTO receipt_items (receipt_id, name, quantity, unit, price, total)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    item_params = (
                        receipt_id,
                        item.get("name"),
                        item.get("quantity"),
                        item.get("unit"),
                        item.get("price"),
                        item.get("total")
                    )
                    execute_query(item_query, item_params, fetch=False)

        return RedirectResponse(url=f"/details/{receipt_id}", status_code=303)

    except Exception as e:
        print("🔥 Upload Error:", e)
        return HTMLResponse(content=f"<h3>❌ Server Error: {e}</h3>", status_code=500)

@app.get("/details/{receipt_id}", response_class=HTMLResponse)
def receipt_details(receipt_id: int, request: Request):
    try:
        result = execute_query("SELECT * FROM receipts1 WHERE id = %s", (receipt_id,))
        if not result:
            return HTMLResponse("<h3>❌ Receipt not found</h3>", status_code=404)

        receipt = result[0]
        stats = compute_stats([receipt])  # Optional, for visual/stat analytics

        # Vendor and date-based charts
        vendor = receipt[1]
        date = receipt[2]
        amount = receipt[3]

        pie_fig = px.pie(
            names=[vendor],
            values=[amount],
            title="Vendor-wise Spending"
        )
        pie_html = pie_fig.to_html(full_html=False)

        bar_fig = px.bar(
            x=[date],
            y=[amount],
            title="Date vs Amount",
            labels={"x": "Date", "y": "Amount"},
            color_discrete_sequence=["#6a0dad"]
        )
        bar_html = bar_fig.to_html(full_html=False)

        items = execute_query(
            "SELECT name, quantity, unit, price, total FROM receipt_items WHERE receipt_id = %s",
            (receipt_id,)
        )

        return templates.TemplateResponse("details.html", {
            "request": request,
            "receipt": receipt,
            "stats": stats,
            "items": items,
            "pie_chart": pie_html,
            "bar_chart": bar_html
        })

    except Exception as e:
        print("🔎 Detail Error:", e)
        return HTMLResponse(content=f"<h3>❌ Error: {e}</h3>", status_code=500)
