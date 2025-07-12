from ultralytics import YOLO
loaded_age_model = None

def load_age_model(model_path):
    global loaded_age_model
    if loaded_age_model is None:
        try:
            loaded_age_model = YOLO(model_path)
            print(f"Yaş Modeli başarıyla yüklendi: {model_path}")
        except Exception as e:
            raise ValueError(f"Yaş Modeli yüklenirken hata oluştu: {e}")

def age_prediction(face_img):
    global loaded_age_model
    if loaded_age_model is None:
        raise ValueError("Yaş modeli yüklü değil. Lütfen önce load_age_model() fonksiyonunu çağırın.")

    age_classes = ['0-10', '11-20', '21-40', '41-60']

    # YOLO ile tahmin yap
    results = loaded_age_model.predict(source=face_img, imgsz=320, conf=0.5)

    # Yaş sınıflarını çıkar
    age_predictions = []
    for result in results:
        if result.boxes is not None:
            for box in result.boxes:
                class_id = int(box.cls)  # Tahmin edilen sınıf ID'si
                confidence = float(box.conf)  # Güven skoru
                age_class = age_classes[class_id]  # Sınıf adını al
                age_predictions.append({
                    'age_class': age_class,
                    'confidence': confidence
                })

    return age_predictions

# Yaş Modeli yolu
AGE_MODEL_PATH = r"C:\Users\ksmcn\PycharmProjects\pythonProject\models\best_age.pt"

# Yaş modelini yükle
load_age_model(AGE_MODEL_PATH)

