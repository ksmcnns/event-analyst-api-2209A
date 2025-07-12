import random
import psycopg2
import cv2
from retinaface import RetinaFace
from deepface.basemodels import VGGFace, Facenet
from faceData import FaceData
import os

model = VGGFace.loadModel()  # (224,224,3)
# model = Facenet.loadModel() #(160,160,3)

def resize_images(image_dir, width, height):
    # Check the existence of the folder
    if not os.path.exists(image_dir):
        print(f"Directory '{image_dir}' does not exist.")
        exit()

    # Select image files
    image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    # Process each image file
    for image_file in image_files:
        # Image path
        image_path = os.path.join(image_dir, image_file)

        # Read the image
        img = cv2.imread(image_path)

        # Resize the image to the specified width and height
        resized_img = cv2.resize(img, (width, height))

        # Write the resized image back to the source location
        cv2.imwrite(image_path, resized_img)

    print("Resizing the image process is completed.")
def extract_faces():
    # Database Connection
    conn = psycopg2.connect(
        host='localhost',
        port='5433',
        database='dbproject',
        user='ksmcnns',
        password='Ks.31213000',
    )
    cursor = conn.cursor()

    # Her bir person_id için kayıt sayısını ve yüz tespiti işlemlerini yap
    cursor.execute("SELECT person_id, COUNT(*) FROM embeddings GROUP BY person_id ORDER BY person_id;")
    person_counts = cursor.fetchall()

    # İterasyon ve işlemler
    for person_id, count in person_counts:
        # Veritabanından kayıtları çek
        cursor.execute(f"SELECT path, embedding FROM embeddings WHERE person_id = {person_id};")
        rows = cursor.fetchall()
        extracted_face_data_list = []

        for i in range(len(rows)):
            # Mevcut kaydın embeddingini al
            current_row = rows[i]
            exist_embedding = current_row[1]
            existing_embedding = [float(num) for num in exist_embedding.strip("[]").split(",")]

            # Embedding ve path'i al
            current_path = current_row[0]

            # Yüz tespiti ve embedding oluştur
            img = cv2.imread(current_path)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            obj = RetinaFace.detect_faces(img)

            if obj is not None:
                for key in obj.keys():
                    identity = obj[key]
                    facial_area = identity['facial_area']

                    # Check if the width or height is less than 10 pixels
                    if facial_area[2] - facial_area[0] < 10 or facial_area[3] - facial_area[1] < 10:
                        continue  # Skip faces with small rectangles

                    # Extract the facial area from the image
                    face_img = img[facial_area[1]:facial_area[3], facial_area[0]:facial_area[2]]

                    # Crop face
                    x = facial_area[0]
                    y = facial_area[1]
                    w = facial_area[2]
                    h = facial_area[3]

                    # Arttırma miktarı
                    increase_width = 50
                    increase_height = 50

                    # Genişlik ve yüksekliği artırarak yeni koordinatları hesapla
                    new_x = max(0, x - increase_width // 2)
                    new_y = max(0, y - increase_height // 2)
                    new_w = w + increase_width
                    new_h = h + increase_height

                    # Resmi cropla
                    cropped_face = img[new_y:new_h, new_x:new_w]
                    cropped_face = cv2.cvtColor(cropped_face, cv2.COLOR_BGR2RGB)

                    # Resize the facial area to match the model's input shape
                    face_img = cv2.resize(face_img, (224, 224))

                    # Expand dimensions to create a batch with a single sample
                    face_img = face_img.reshape(1, *face_img.shape)

                    # Predict embeddings using the model
                    vector_embedding = model.predict(face_img)

                    # Flatten the face_embedding array to a 1D array
                    current_embedding = [item for sublist in vector_embedding for item in sublist]

                    distance = calculate_distance_of_embeddings(existing_embedding, current_embedding)

                    # Eğer mesafe sıfırsa, yüzü kes ve yeni bir dosyaya kaydet
                    if distance <= 0.1:

                        # Define the directory path
                        cropped_faces_dir = 'C:\\Users\\ksmcn\\PycharmProjects\\pythonProject\\images\\croppedFaces'
                        # Check if the directory exists, and create it if not
                        if not os.path.exists(cropped_faces_dir):
                            os.makedirs(cropped_faces_dir)
                        cropped_face_path = os.path.join(cropped_faces_dir, 'cf{}{}{}.jpg'.format(person_id, key,random_numbers()))
                        # Save the cropped face image
                        cv2.imwrite(cropped_face_path, cropped_face)

                        # filling face_data_list
                        face_data = FaceData(person_id=person_id, image_path=cropped_face_path,
                                             age=None, age_accuracy=None, gender_accuracy=None,
                                             gender=None, race=None, race_accuracy=None,
                                             embedding=current_embedding, check_status=False)
                        face_data.add_data(person_id=person_id, image_path=cropped_face_path,
                                           age=None, age_accuracy=None, gender=None,
                                           gender_accuracy=None, race=None, race_accuracy=None,
                                           embedding=current_embedding, check_status=False)
                        print(face_data)
                        extracted_face_data_list.append(face_data)

                print('face extracted')
        send_to_database(extracted_face_data_list)
    conn.close()
def random_numbers():
     random_sayi = random.randint(1, 1000)
     return random_sayi
def send_to_database(face_data_list):
    # Database Connection
    conn = psycopg2.connect(
        host='localhost',
        port='5432',
        database='dbproject',
        user='ksmcnns',
        password='Ks.31213000',
    )
    cursor = conn.cursor()

    # İstatistik tablosunu oluştur
    cursor.execute("""
              CREATE TABLE IF NOT EXISTS statistic (
                  id SERIAL PRIMARY KEY,
                  person_id INT,
                  age VARCHAR,
                  gender VARCHAR,
                  race VARCHAR,
                  face_path VARCHAR
              );
          """)

    # Add data from the FaceData list to the table
    for face_data in face_data_list:
        person_id = face_data.person_id
        age = None
        gender = None
        race = None
        image_path = os.path.normpath(face_data.image_path)

        # Use ARRAY[] to add the 1D array to PostgreSQL
        statement = f"""
                                 INSERT INTO 
                                 statistic
                                 (person_id, age, gender, race, face_path)
                                 VALUES 
                                 ({person_id}, '{age}', '{gender}','{race}', '{image_path}');
                    """
        cursor.execute(statement)
        conn.commit()
def calculate_distance_of_embeddings(existEmbedding,currEmbedding):
    # Database Connection
    conn = psycopg2.connect(
        host='localhost',
        port='5432',
        database='dbproject',
        user='ksmcnns',
        password='Ks.31213000',
    )
    cursor = conn.cursor()

    # Create distance table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS distance (
            id SERIAL PRIMARY KEY,
            existEmbedding VECTOR(2622),
            currEmbedding VECTOR(2622)
        );
    """)

    # Save embeddings
    statement = f"""
    INSERT INTO 
    distance
    (currEmbedding, existEmbedding)
    VALUES 
    (ARRAY{currEmbedding}, ARRAY{existEmbedding});
"""
    cursor.execute(statement)
    # Calculate distance
    sql_query = """
        SELECT
            id,
            currEmbedding,
            existEmbedding,
            currEmbedding <=> (SELECT existEmbedding FROM distance WHERE id = 1) AS distance
        FROM
            distance
        WHERE
            id = 1;
    """
    cursor.execute(sql_query)
    result = cursor.fetchone()
    cursor.close()

    distance_value = result[3]
    conn.close()
    return distance_value
def readImagesFromDirectory(image_dir):

    existing_image_paths = []
    # Check the existence of the folder
    if not os.path.exists(image_dir):
        print(f"Directory '{image_dir}' does not exist.")
        return existing_image_paths  # Return empty list if directory doesn't exist
    # Select image files
    image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    # Construct full paths for the image files
    existing_image_paths = [os.path.join(image_dir, img) for img in image_files]
    return existing_image_paths