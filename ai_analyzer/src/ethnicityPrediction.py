import cv2
import torch
from torchvision import models, transforms

# Modeli yalnızca bir kez yükle
loaded_model = None

def load_ethnicity_model(model_path):
    global loaded_model
    if loaded_model is None:
        try:
            # ResNet18 modelini instantiate et
            model = models.resnet18(pretrained=False)  # pretrained=False çünkü kendi ağırlıklarınızı yüklüyorsunuz
            num_ftrs = model.fc.in_features
            model.fc = torch.nn.Linear(num_ftrs, 4)  # 4 sınıf için çıkış katmanı (White, Black, Asian, Indian)

            # Model dosyasını yükle
            state_dict = torch.load(model_path, map_location=torch.device('cuda' if torch.cuda.is_available() else 'cpu'))

            # State dictionary'deki anahtarları "resnet." önekinden temizle
            new_state_dict = {}
            for k, v in state_dict.items():
                if k.startswith('resnet.'):
                    new_key = k.replace('resnet.', '', 1)  # "resnet." önekini kaldır
                    new_state_dict[new_key] = v
                else:
                    new_state_dict[k] = v  # Önek yoksa olduğu gibi al

            # Temizlenmiş state dictionary'yi modele yükle
            model.load_state_dict(new_state_dict, strict=True)
            model.eval()  # Modeli değerlendirme moduna al
            loaded_model = model
            print(f"Model başarıyla yüklendi: {model_path}")
        except Exception as e:
            raise ValueError(f"Model yüklenirken hata oluştu: {e}")

def ethnicity_prediction(face_img):
    global loaded_model
    if loaded_model is None:
        raise ValueError("Model is not loaded. Please call load_ethnicity_model() first.")

    # Resmi 320x320 boyutuna getir (ResNet18 genelde 224x224 bekler, dikkat!)
    face_img = cv2.resize(face_img, (224,224))
    ethnicity_classes = ['White', 'Black', 'Asian', 'Indian']
    # Görüntüyü PyTorch tensörüne dönüştür
    transform = transforms.Compose([
        transforms.ToTensor(),  # BGR -> RGB, 0-255 -> 0-1
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])  # ResNet varsayılan normalizasyonu
    ])
    face_img = transform(face_img).unsqueeze(0)  # Batch boyutu ekle (1, 3, 320, 320)

    # GPU kullanılabiliyorsa modele gönder
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    loaded_model = loaded_model.to(device)
    face_img = face_img.to(device)

    # Tahmin yap
    try:
        with torch.no_grad():
            output = loaded_model(face_img)
            probabilities = torch.nn.functional.softmax(output, dim=1)
            conf, class_id = torch.max(probabilities, 1)
            pred_ethnicity = ethnicity_classes[class_id.item()]
            return pred_ethnicity, conf.item()
    except Exception as e:
        print(f"Tahmin sırasında hata oluştu: {e}")
        return None, 0.0

# Model yolu
MODEL_PATH = r"C:\Users\ksmcn\PycharmProjects\pythonProject\models\ethnicity_model.pth"

# Modeli yükle
load_ethnicity_model(MODEL_PATH)
