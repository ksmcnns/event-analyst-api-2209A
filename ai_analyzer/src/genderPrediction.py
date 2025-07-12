
from ultralytics import YOLO

loaded_gender_model = None  # Cinsiyet modeli için ayrı bir global değişken kullanın

def load_gender_model(model_path):
    global loaded_gender_model
    if loaded_gender_model is None:
        try:
            loaded_gender_model = YOLO(model_path)
            print(f"Cinsiyet Modeli başarıyla yüklendi: {model_path}")
        except Exception as e:
            raise ValueError(f"Cinsiyet Modeli yüklenirken hata oluştu: {e}")

def gender_prediction(face_img):
    global loaded_gender_model
    if loaded_gender_model is None:
        raise ValueError("Cinsiyet modeli yüklü değil. Lütfen önce load_gender_model() fonksiyonunu çağırın.")

    gender_classes = ['Female', 'Male']

    results = loaded_gender_model.predict(source=face_img, imgsz=320,
                                          conf=0.45)  # Örneğin conf=0.25 veya 0.5 gibi bir değer kullanın

    male_confidence = -1.0
    female_confidence = -1.0

    for result in results:
        if result.boxes is not None:
            for box in result.boxes:
                class_id = int(box.cls)
                confidence = float(box.conf)

                if gender_classes[class_id] == 'Male':
                    male_confidence = max(male_confidence, confidence)
                elif gender_classes[class_id] == 'Female':
                    female_confidence = max(female_confidence, confidence)


    final_gender_class = None
    final_confidence = 0.0

    if male_confidence >= 0 or female_confidence >= 0:  # En az bir tahmin geldiyse
        if male_confidence > female_confidence:
            final_gender_class = 'Male'
            final_confidence = male_confidence
        elif female_confidence > male_confidence:
            final_gender_class = 'Female'
            final_confidence = female_confidence
        else:
            if male_confidence == -1.0 and female_confidence == -1.0:
                final_gender_class = 'Male'
                final_confidence = 0.0
            else:
                final_gender_class = 'Male'
                final_confidence = male_confidence
    if final_gender_class is None:
        final_gender_class = 'Male'
        final_confidence = 0.0

    return [{'gender_class': final_gender_class, 'confidence': final_confidence}]

GENDER_MODEL_PATH = r"C:\Users\ksmcn\PycharmProjects\pythonProject\models\best_gender.pt"

load_gender_model(GENDER_MODEL_PATH)