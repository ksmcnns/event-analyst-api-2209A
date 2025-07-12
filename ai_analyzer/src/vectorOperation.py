import os
import cv2
import psycopg2
from insightface.app import FaceAnalysis
from retinaface import RetinaFace
# argparse artık burada kullanılmayacak, bu yüzden kaldırabiliriz
# import argparse

from ai_analyzer.src.agePrediction import age_prediction
from ai_analyzer.src.genderPrediction import gender_prediction
from ai_analyzer.src.ethnicityPrediction import ethnicity_prediction
from ai_analyzer.src.faceData import FaceData
from ai_analyzer.src.databaseOperation import groupe_vectors, reset_database_and_directory

# InsightFace modellerini ve RetinaFace modelini global olarak veya
# bir kez başlatılacak şekilde dışarı taşıyabiliriz.
# Bu, her get_json_result_using_path_array çağrısında modellerin yeniden yüklenmesini önler.
# Ancak başlangıçta basitlik için fonksiyonun içine koyalım,
# performans sorunu olursa dışarı taşımayı düşünebiliriz.

# Global olarak FaceAnalysis ve RetinaFace instance'larını tutmak için değişkenler
# Uygulama başladığında bir kez başlatılacaklar.
global_face_analysis_app = None
global_retinaface_model = None

def initialize_ai_models(ctx_id=0, det_size=640):
    """
    Yapay zeka modellerini bir kez başlatır.
    """
    global global_face_analysis_app
    global global_retinaface_model

    if global_face_analysis_app is None:
        print(f"AI modelleri başlatılıyor: ctx_id={ctx_id}, det_size={det_size}")
        # GPU'yu devre dışı bırak, CPU kullan (bu env var sadece bir kez ayarlanmalı)
        os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

        # RetinaFace modelini yükle
        global_retinaface_model = RetinaFace.build_model()

        # InsightFace modelini hazırla
        model_pack_name = 'buffalo_l'
        global_face_analysis_app = FaceAnalysis(name=model_pack_name, providers=['CPUExecutionProvider'])
        # Modeli hazırla
        global_face_analysis_app.prepare(ctx_id=ctx_id, det_size=(det_size, det_size))
        print("AI modelleri başarıyla başlatıldı.")
    else:
        print("AI modelleri zaten başlatılmış.")


def get_json_result_using_path_array(pathArray, ctx_id=0, det_size=640):
    """
    Verilen resim yollarındaki yüzleri analiz eder ve istatistikleri döndürür.
    """
    # Modellerin başlatıldığından emin ol
    initialize_ai_models(ctx_id, det_size)

    # Global değişkenleri kullanarak modellere eriş
    app = global_face_analysis_app
    # retinaface_model = global_retinaface_model # Şu an retinaface_model kullanılmıyor gibi görünüyor,
                                                # eğer kullanılıyorsa buraya eklenmeli

    # Store face attributes
    face_data_list = []

    for image_path in pathArray:
        # Resim okuma ve dönüşümler
        img = cv2.imread(image_path)
        if img is None:
            print(f"Uyarı: {image_path} adresindeki resim okunamadı. Atlanıyor.")
            continue
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Yüzleri tespit et ve embedding'leri al
        faces = app.get(rgb_img)

        for face in faces:
            bbox = face.bbox.astype(int)

            # Genişlik veya yükseklik 10 pikselden küçükse atla
            if (bbox[2] - bbox[0] < 10) or (bbox[3] - bbox[1] < 10):
                continue

            # Yüz resmini çıkar
            face_img = rgb_img[bbox[1]:bbox[3], bbox[0]:bbox[2]]

            # Geçersiz yüz resimlerini atla
            if face_img.size == 0 or face_img.shape[0] == 0 or face_img.shape[1] == 0:
                continue

            # Embedding vektörünü al
            embedding = face.normed_embedding

            # Yaş, cinsiyet ve etnik kökeni tahmin et - HAM çıktıları al
            # Burada 'raw_pred_gender' vb. değişkenlerin beklenen formatını ve
            # 'gender_prediction' gibi fonksiyonların çıktılarını kontrol etmek önemlidir.
            raw_pred_gender = gender_prediction(face_img)
            raw_pred_age = age_prediction(face_img)
            raw_pred_ethnicity = ethnicity_prediction(face_img)

            # Cinsiyet
            gender = 'Unknown'
            if raw_pred_gender and isinstance(raw_pred_gender, list) and len(raw_pred_gender) > 0:
                # `gender_class` anahtarının varlığını kontrol et
                if isinstance(raw_pred_gender[0], dict) and 'gender_class' in raw_pred_gender[0]:
                    gender = raw_pred_gender[0]['gender_class']
                elif isinstance(raw_pred_gender[0], str): # Eğer doğrudan string dönüyorsa
                    gender = raw_pred_gender[0]


            # Yaş
            age = 3 # Varsayılan olarak 41+ olarak ayarlanabilir
            pred_age_class_str = 'Unknown'
            if raw_pred_age and isinstance(raw_pred_age, list) and len(raw_pred_age) > 0:
                # `age_class` anahtarının varlığını kontrol et
                if isinstance(raw_pred_age[0], dict) and 'age_class' in raw_pred_age[0]:
                    pred_age_class_str = raw_pred_age[0]['age_class']
                elif isinstance(raw_pred_age[0], str): # Eğer doğrudan string dönüyorsa
                    pred_age_class_str = raw_pred_age[0]


            if pred_age_class_str == "0-10":
                age = 0
            elif pred_age_class_str == "11-20":
                age = 1
            elif pred_age_class_str == "21-40":
                age = 2
            elif pred_age_class_str == "41+": # Daha net bir kategori ekledim
                age = 3
            # Eğer başka yaş aralıkları varsa buraya eklenebilir.


            # Etnik Köken (Race)
            race = 'Unknown'
            # Tuple kontrolü ve len kontrolü doğru, ama içindeki değerin string olduğundan emin ol
            if isinstance(raw_pred_ethnicity, tuple) and len(raw_pred_ethnicity) > 0:
                if isinstance(raw_pred_ethnicity[0], str):
                    race = raw_pred_ethnicity[0]
                elif isinstance(raw_pred_ethnicity[0], dict) and 'race_class' in raw_pred_ethnicity[0]: # Tahmini anahtar adı
                    race = raw_pred_ethnicity[0]['race_class']


            face_data = FaceData(
                check_status=False, result_status=False, person_id=0, image_path=image_path,
                age=age, age_accuracy=None, gender_accuracy=None,
                gender=gender, race=race, race_accuracy=None, embedding=embedding.tolist()
            )
            # add_data metodu zaten constructor'da yapılan işi tekrarlıyor gibi.
            # Eğer ek bir kontrol/güncelleme yapmıyorsa bu çağrı gereksiz olabilir.
            # Eğer FaceData nesnesinin içindeki bir listeye ekleme yapıyorsa kalsın.
            face_data.add_data(
                check_status=False, result_status=False, person_id=0, age=age, gender=gender,
                age_accuracy=None, gender_accuracy=None, race=race, race_accuracy=None,
                embedding=embedding.tolist(), image_path=image_path
            )
            face_data_list.append(face_data)

    # Veritabanı bağlantısı ve işlemleri
    conn = None # conn'i try bloğu dışında tanımla
    try:
        conn = psycopg2.connect(
            host='localhost',
            port='5433',
            database='dbproject',
            user='ksmcnns',
            password='Ks.31213000',
        )
        cursor = conn.cursor()

        # Tablo yoksa oluştur
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vector_table (
                id SERIAL PRIMARY KEY,
                check_status BOOLEAN,
                person_id INT,
                path VARCHAR,
                age INT,
                gender VARCHAR,
                race VARCHAR,
                embedding vector(512)
            );
        """)

        # FaceData listesinden verileri tabloya ekle
        for face_data in face_data_list:
            check_status = False
            person_id = 0
            image_path = os.path.normpath(face_data.image_path)
            age = face_data.age
            gender = face_data.gender
            race = face_data.race
            face_embedding = face_data.embedding

            statement = """
                INSERT INTO vector_table (check_status, person_id, path, age, gender, race, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(statement, (
                check_status, person_id, image_path, age, gender, race, face_embedding))

        conn.commit() # Değişiklikleri kaydet
        cursor.close()

    except Exception as e:
        if conn:
            conn.rollback() # Hata durumunda geri al
        print(f"Veritabanı işlemi sırasında hata oluştu: {e}")
        # Hatanın daha yukarı taşınması için yeniden fırlatılabilir: raise e
        raise # Bu, hatayı Django view'ine geri fırlatacak

    finally:
        if conn:
            conn.close() # Bağlantıyı kapat


    # Gruplama ve sonuçları al
    json_result = groupe_vectors('vector_table')

    # Veritabanı tablolarını bırak ve croppedFaces dizinindeki tüm resimleri sil
    db_host = 'localhost'
    db_port = '5433'
    db_name = 'dbproject'
    db_user = 'ksmcnns'
    db_password = 'Ks.31213000'
    directory_path = 'C:\\Users\\ksmcn\\PycharmProjects\\pythonProject\\images\\croppedFaces'

    # Resetleme işlemi
    reset_database_and_directory(db_host, db_port, db_name, db_user, db_password, directory_path)

    return json_result

