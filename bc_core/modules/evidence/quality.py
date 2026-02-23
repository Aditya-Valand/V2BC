import cv2

def image_quality_score(path):
    img = cv2.imread(path, 0)
    if img is None:
        return 0
    return cv2.Laplacian(img, cv2.CV_64F).var()
