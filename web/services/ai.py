import os
from google import genai
from google.genai import types
import pathlib

client = genai.Client()

def generate_text(prompt, max_tokens=150):
    response = client.generate_text(
        model="gemini-1.5-pro",
        prompt=prompt,
        max_output_tokens=max_tokens
    )
    return response.text


def process_pdf(prompt, path):
    filepath = pathlib.Path(path)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(
                data=filepath.read_bytes(),
                mime_type='application/pdf',
            ), prompt]
        )

    return response.text
