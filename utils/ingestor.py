import os
import base64
from docling.document_converter import DocumentConverter
from langchain_core.messages import HumanMessage
from config import GLOBAL_LLM


class RobustIngestor:
    def __init__(self, input_file):
        self.input_file = input_file
        self.llm = GLOBAL_LLM

    def extract_text_from_image(self) -> str:
        print("[INFO] Using Gemini to extract text from image...")
        with open(self.input_file, "rb") as img_file:
            image_data = img_file.read()
            base64_image = base64.b64encode(image_data).decode("utf-8")

        response = self.llm.invoke(
            [
                HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": """
You are an expert invoice extraction assistant.

You will be given an image of a **handwritten Indian invoice**. Your task is to **accurately extract all visible data** from the image and return it as a **valid JSON object**.

⚠️ The image may be handwritten, tilted, noisy, or partially faded. Extract only what is clearly readable. If a field is missing or unreadable, use `""` for strings or `0` / `0.0` for numbers.

---

🎯 Output JSON schema (use **this structure exactly**):

```json
{
  "short_summary_of_invoice": "", // A brief summary of the invoice (e.g., "Grocery bill from Sharma Kirana Store")
  "invoice_number": "",        // Bill number or reference code
  "date": "",                  // Bill date (preferred format: YYYY-MM-DD)
  "vendor_name": "",           // Name of the shop or supplier
  "Phone_No": "",              // Vendor contact number (if visible)
  "items": [
    {
      "name": "",              // Item name or description
      "qty": 0,                // Quantity (integer or float)
      "rate": 0.0,             // Price per unit (₹)
      "price": 0.0             // Total price for that item
    }
  ],
  "total_quantity": 0,         // Sum of item quantities
  "total_amount": 0.0          // Grand total payable (₹)
}---

### ✅ Output example expected from LLM:

```json
{
  "short_summary_of_invoice": "Grocery bill from Sharma Kirana Store on June 30, 2025 having 2 diffrent items",
  "invoice_number": "INV-101",
  "date": "2025-06-30",
  "vendor_name": "Sharma Kirana Store",
  "Phone_No": "9876543210",
  "items": [
    { "name": "Basmati Rice","qty": 2,"rate": 60.0,"price": 120.0 },
    {"name": "Sugar","qty": 1,"rate": 45.0,"price": 45.0}
  ],
  "total_quantity": 3,
  "total_amount": 165.0
}""",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ]
                )
            ]
        )
        return str(response.content)

    def convert_document(self) -> str:
        print("[INFO] Converting document to markdown using docling...")
        converter = DocumentConverter()
        result = converter.convert(self.input_file)
        return result.document.export_to_markdown()

    def run(self) -> str:
        file_ext = os.path.splitext(self.input_file)[-1].lower()
        if file_ext in (".jpeg", ".jpg", ".png"):
            text = self.extract_text_from_image()
        else:
            text = self.convert_document()

        return text


if __name__ == "__main__":
    input_file = "/Users/hamza/Developer/Imp_Projects/smart_shop/documents/WhatsApp Image 2025-06-17 at 8.16.58 PM.jpeg"  # or "image1.jpeg"
    ingestor = RobustIngestor(input_file=input_file)
    text = ingestor.run()


# {
#   "invoice_number": "848",
#   "date": "2022-09-30",
#   "vendor_name": "CIST Corporation",
#   "Phone_No": "9009303572",
#   "items": [
#     {
#       "name": "O' Hinges doritoss",
#       "qty": 15,
#       "rate": 125.0,
#       "price": 1875.0
#     },
#     {
#       "name": "0° Ebro soft close",
#       "qty": 10,
#       "rate": 165.0,
#       "price": 1650.0
#     },
#     {
#       "name": "O' Hafele",
#       "qty": 4,
#       "rate": 295.0,
#       "price": 1180.0
#     },
#     {
#       "name": "8° Hafele",
#       "qty": 6,
#       "rate": 310.0,
#       "price": 1860.0
#     },
#     {
#       "name": "20 Hafele",
#       "qty": 6,
#       "rate": 385.0,
#       "price": 2310.0
#     },
#     {
#       "name": "18\" Hafele",
#       "qty": 4,
#       "rate": 370.0,
#       "price": 1480.0
#     },
#     {
#       "name": "19X6 (+1",
#       "qty": 500,
#       "rate": 0.0,
#       "price": 195.0
#     },
#     {
#       "name": "O'Ebro",
#       "qty": 3,
#       "rate": 165.0,
#       "price": 495.0
#     },
#     {
#       "name": "O'Ebro",
#       "qty": 3,
# ----------------------------------------

# --- Chunk 2 ---
# "rate": 0.0,
#       "price": 195.0
#     },
#     {
#       "name": "O'Ebro",
#       "qty": 3,
#       "rate": 165.0,
#       "price": 495.0
#     },
#     {
#       "name": "O'Ebro",
#       "qty": 3,
#       "rate": 0.0,
#       "price": 495.0
#     }
#   ],
#   "total_quantity": 541,
#   "total_amount": 10550.0
# }
