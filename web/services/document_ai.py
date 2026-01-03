from google import genai
from google.genai import types
import json
import os


class DocumentAI:
    def __init__(self, api_key: str | None = None):
        # Just store the key, don't use it yet
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        """Only creates the Gemini client when it's actually needed."""
        if self._client is None:
            # Fallback to env variable if no key was passed to __init__
            key = self.api_key or os.getenv("GEMINI_API_KEY")
            if not key:
                raise ValueError("Missing Gemini API Key! Set GEMINI_API_KEY in your .env file.")
            self._client = genai.Client(api_key=key)
        return self._client

    def extract_data(self, image_path: str) -> dict:
        """
        Main pipeline:
        Image → Gemini Vision → Structured JSON
        """
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        prompt = """
        You are an intelligent document parser.

        Extract the following fields from this invoice image:
        - vendor_name
        - invoice_number
        - gstin
        - invoice_date
        - total_amount

        Rules:
        - Return ONLY valid JSON
        - Use null if a field is missing
        - total_amount must be a number (not string)
        - Do NOT add explanations
        """

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/jpeg"
                ),
                prompt
            ]
        )

        return self._safe_json_parse(response.text)

    def _safe_json_parse(self, text: str) -> dict:
        """
        Safely parse JSON even if model adds extra text accidentally.
        """
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # fallback: extract JSON block
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1:
                return json.loads(text[start:end])

            # absolute fallback
            return {
                "vendor_name": None,
                "invoice_number": None,
                "gstin": None,
                "invoice_date": None,
                "total_amount": None,
            }


# ---------------- USAGE ----------------
# ai = DocumentAI()
# result = ai.extract_data("invoice.jpg")
# print(result)
