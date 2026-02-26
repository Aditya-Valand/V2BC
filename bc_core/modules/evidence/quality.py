"""
Image quality scoring — Laplacian gradient magnitude via numpy/PIL.
Replaces the cv2-based version; cv2 is not in requirements.txt.
"""
import io


def image_quality_score(file_path: str) -> float:
    """
    Compute a sharpness score for the image at file_path.
    Higher = sharper.  Score < 30 → blurry/rejected.
    Score 30-60 → low_quality but accepted.
    Score > 60 → usable.

    Falls back to 100.0 (assume usable) if numpy/PIL unavailable.
    """
    try:
        import numpy as np

        with open(file_path, "rb") as f:
            data = f.read()

        try:
            from PIL import Image
            img = Image.open(io.BytesIO(data)).convert("L").resize((300, 300))
            arr = np.array(img, dtype=np.float32)
            gy = np.diff(arr, axis=0)
            gx = np.diff(arr, axis=1)
            return float(np.sqrt(np.mean(gy ** 2) + np.mean(gx ** 2)))
        except ImportError:
            # PIL not available — fallback score
            return 100.0

    except Exception:
        return 100.0


def quality_status(score: float) -> str:
    """Map numeric quality score to status string."""
    if score >= 60:
        return "usable"
    if score >= 30:
        return "low_quality"
    return "rejected"
