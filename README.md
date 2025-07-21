# ocR-app 
Design Choices
Component	Choice	Reason
Backend	FastAPI	Fast, lightweight, async
Database	MySQL	Stable, relational schema for receipts
AI Parser	Gemini 2.0 Flash (LLM)	Great OCR + reasoning on unstructured docs
Templating	Jinja2	Clean integration with HTML
Charts	Plotly	Interactive graphs, no frontend JS required 


 User Journeys
User uploads a receipt (image/pdf)

Gemini LLM extracts structured data

Receipt data is saved in MySQL

Homepage displays total stats

User can click 'More Details' to see:

Full Gemini-parsed data

1) Amount-over-date Plotly graph

2) Vendor & payment stats

3) Sample Graphs Shown
. Amount vs Date (Line Chart)

.Category or Currency breakdown (Bar Chart / Pie Chart) 


Assumptions
Receipts are readable and in English

Gemini LLM API key is valid

MySQL DB and table receipts1 is pre-created

amount field is always numeric

All files are uploaded manually by user (no automation) 


Limitations
No authentication or user-based login system

Not optimized for cloud storage or scale yet

Parsing depends on Gemini accuracy (may fail with poor images)

No duplicate receipt detection

Only supports basic currency detection (not conversion) 

#Architecture# 
<img width="739" height="937" alt="image" src="https://github.com/user-attachments/assets/e8b0fc89-3722-408e-b3ac-5779696376ba" />
