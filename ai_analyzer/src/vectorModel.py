import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis

assert insightface.__version__ >= '0.3'

def create_embeddings(image_path):
    # Initialize InsightFace model
    model_pack_name = 'buffalo_l'
    app = FaceAnalysis(name=model_pack_name)

    # Prepare the model
    app.prepare(ctx_id=0, det_size=(640, 640))

    # Creating embeddings array
    embeddings = []

    # Load the image
    img = cv2.imread(image_path)

    # Use RetinaFace to detect faces
    faces = app.get(img)

    # Check if faces are detected
    if not faces:
        print("RetinaFace could not detect any faces in the image.")
        return []

    for face in faces:
        # Get embedding vector for the aligned face
        embedding = face.normed_embedding

        # Append the embedding to the list
        embeddings.append(embedding)
        print("Size of embedding:", embedding.shape)
        print(embedding)

    return embeddings

# Test the function
create_embeddings("images\\biz.jpg")
