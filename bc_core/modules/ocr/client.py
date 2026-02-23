try:
    from google.cloud import vision
    VISION_PACKAGE_AVAILABLE = True
except ImportError:
    VISION_PACKAGE_AVAILABLE = False
    print("WARNING: Google Cloud Vision not installed. OCR will return mock data.")

# Lazy-load the client to handle missing credentials gracefully
client = None
VISION_AVAILABLE = False

def _get_vision_client():
    """Lazy-load Vision client on first use."""
    global client, VISION_AVAILABLE
    if VISION_AVAILABLE:
        return client
    if not VISION_PACKAGE_AVAILABLE:
        return None
    try:
        if client is None:
            client = vision.ImageAnnotatorClient()
        VISION_AVAILABLE = True
        return client
    except Exception as e:
        print(f"WARNING: Could not initialize Google Vision client: {e}. OCR will return mock data.")
        VISION_AVAILABLE = False
        return None


def extract_text(image_path):
    """Extract text from an image using Google Cloud Vision API"""
    vision_client = _get_vision_client()
    if not vision_client:
        # Return mock data for development
        return "Mock OCR text extracted from image", []
    
    try:
        with open(image_path, "rb") as f:
            content = f.read()

        image = vision.Image(content=content)
        response = vision_client.text_detection(image=image)

        if response.error.message:
            raise Exception(response.error.message)

        texts = response.text_annotations

        full_text = texts[0].description if texts else ""
        blocks = []

        for t in texts[1:]:
            blocks.append({
                "text": t.description,
                "confidence": None
            })

        return full_text, blocks
    except Exception as e:
        print(f"Error extracting text: {str(e)}")
        # Return mock data on error
        return "Error extracting text from image", []
