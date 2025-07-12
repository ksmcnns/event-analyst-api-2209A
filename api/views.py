import json
import traceback

from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth import update_session_auth_hash
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import login

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.exceptions import PermissionDenied

from knox.auth import TokenAuthentication
from knox.views import LoginView as KnoxLoginView
from knox.models import AuthToken

import jwt

from ai_analyzer.src.vectorOperation import get_json_result_using_path_array
from .serializers import (
    UserSerializer,
    EmailVerificationSerializer,
    ChangePasswordSerializer,
    EventSerializer,
    PhotoSerializer,
    AuthSerializer,
    EventStatisticSerializer,
)
from .models import CustomUser, Event, Photo, EventStatistic
from .utils import Util


# USER VIEWS


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            token = RefreshToken.for_user(user).access_token

            current_site = get_current_site(request).domain
            relative_link = reverse("email_verify")
            abs_url = "http://" + current_site + relative_link + "?token=" + str(token)
            email_body = (
                "Hi "
                + user.username
                + " Use link below to verify your email\n"
                + abs_url
            )
            data = {
                "email_body": email_body,
                "to_email": user.email,
                "email_subject": "Verify your email",
            }

            Util.send_email(data)
            response_data = (
                {
                    "message": "User registered successfully. Verification email sent.",
                    "user": {
                        "username": user.username,
                        "email": user.email,
                    },
                },
            )

            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginUserView(KnoxLoginView):
    serializer_class = AuthSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        ''' if not user.is_verified:
            return Response(
                {"detail": "User account is not verified"},
                status=status.HTTP_403_FORBIDDEN,
            )
        '''
        login(request, user)
        response = super(LoginUserView, self).post(request, format=None)
        response_data = response.data
        response_data["user"]["email"] = user.email
        response_data["user"]["is_verified"] = user.is_verified

        return Response(response_data)


def get_token_expiry(user):
    try:
        token = AuthToken.objects.filter(user=user).latest("expiry")
        return {"expiry": token.expiry}
    except AuthToken.DoesNotExist:
        return None


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def get(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(user)
        token_expiry = get_token_expiry(user)
        data = serializer.data
        data["token_expiry"] = token_expiry
        return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    if request.method == "POST":
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data.get("new_password"))
            user.save()
            update_session_auth_hash(request, user)
            return Response(
                {"message": "Password changed successfully"},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(generics.GenericAPIView):
    serializer_class = EmailVerificationSerializer

    def get(self, request):
        token = request.GET.get("token")
        print(token)
        try:
            print("\ntrying somethin\n")
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms="HS256")
            user = CustomUser.objects.get(id=payload["user_id"])
            if not user.is_verified:
                user.is_verified = True
                user.save()
            return Response(
                {"email": "Successfully activated"}, status=status.HTTP_201_CREATED
            )
        except jwt.ExpiredSignatureError as identifier:
            return Response(
                {"error": "Activation expired"}, status=status.HTTP_400_BAD_REQUEST
            )
        except jwt.exceptions.DecodeError as identifier:
            return Response(
                {"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST
            )


class ResendActivationEmailView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.is_verified:
            return Response(
                {"detail": "Kullanıcı zaten aktif."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken.for_user(user).access_token
            current_site = get_current_site(request).domain
            relativeLinks = reverse("email_verify")
            absurl = "http://" + current_site + relativeLinks + "?token=" + str(token)
            email_body = (
                "Hi "
                + user.username
                + " Use link below to verify your email\n"
                + absurl
            )
            data = {
                "email_body": email_body,
                "to_email": user.email,
                "email_subject": "Verify your email",
            }

            Util.send_email(data)
            return Response(
                {"detail": "Resend activation mail, please check your mail"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            print(e)
            return Response(
                {"detail": "Activation mail couldn't send"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# EVENT VIEWS


@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_event(request):
    if request.method == "POST":
        serializer = EventSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            event = serializer.save()
            response_serializer = EventSerializer(event)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EventDetailView(generics.RetrieveAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        eventId = self.kwargs.get("eventId")
        event = Event.objects.get(eventId=eventId)
        if event.event_owner != self.request.user:
            raise PermissionDenied("Event not found")
        return Event.objects.get(eventId=eventId)


@api_view(["GET"])
def get_all_events(request):
    user_events = Event.objects.filter(event_owner=request.user)
    serializer = EventSerializer(user_events, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
def delete_event(request, event_id):
    if request.method == "DELETE":
        try:
            event = Event.objects.get(eventId=event_id)
        except Event.DoesNotExist:
            return Response(
                {"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if event.event_owner != request.user:
            return Response(
                {"error": "Event not found"},
                status=status.HTTP_403_FORBIDDEN,
            )

        event.delete()
        return Response(
            {"message": "Event deleted successfully"}, status=status.HTTP_204_NO_CONTENT
        )


@api_view(["PUT"])  # event_title necessary
def update_event(request, event_id):
    try:
        event = Event.objects.get(eventId=event_id, event_owner=request.user)
    except Event.DoesNotExist:
        return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = EventSerializer(event, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PATCH"])
def partial_update_event(request, event_id):
    try:
        event = Event.objects.get(eventId=event_id, event_owner=request.user)
    except Event.DoesNotExist:
        return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = EventSerializer(event, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Event Statistic Creation
@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_event_statistic(request, event_id):
    try:
        event = Event.objects.get(eventId=event_id)
    except Event.DoesNotExist:
        return Response({"error": "Etkinlik bulunamadı."}, status=status.HTTP_404_NOT_FOUND)

    if event.event_owner != request.user:
        return Response(
            {"error": "Bu etkinliğin sahibi değilsiniz."},
            status=status.HTTP_403_FORBIDDEN
        )

    photos = Photo.objects.filter(event=event)
    if not photos.exists():
        return Response(
            {"error": "Bu etkinlik için fotoğraf bulunamadı."},
            status=status.HTTP_400_BAD_REQUEST
        )

    image_paths = [photo.path.path for photo in photos]
    try:
        raw_json_string = get_json_result_using_path_array(image_paths)
        json_result = json.loads(raw_json_string)

    except json.JSONDecodeError as e:
        print(f"HATA: AI analizinden dönen JSON verisi ayrıştırılamadı: {e}")
        traceback.print_exc()
        return Response(
            {"error": f"AI analizinden dönen JSON verisi ayrıştırılamadı: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        print(f"HATA: Resimler işlenirken beklenmedik bir hata oluştu: {e}")
        traceback.print_exc()
        return Response(
            {"error": f"Resimler işlenirken beklenmedik bir hata oluştu: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # İstatistik verilerini hazırlama
    data = {
        "event": event.eventId, # OneToOneField için event objesinin PK'sini geçmek daha güvenli
                           # event.eventId ile aynı değer olmalı
        "genderAnalysis": json_result["gender_counts"],
        "raceAnalysis": json_result["race_counts"],
        "ageAnalysis": json_result["age_distribution"],
    }
    print(f"Analiz Verisi: {data}")
    # Mevcut istatistiği bul veya yeni bir tane oluştur
    try:
        statistic_instance = EventStatistic.objects.get(event=event)
        # Eğer varsa, güncelleyeceğiz (PUT/PATCH gibi davranırız)
        serializer = EventStatisticSerializer(instance=statistic_instance, data=data, partial=False)
        status_code = status.HTTP_200_OK # Güncelleme başarılıysa 200 OK
    except EventStatistic.DoesNotExist:
        # Eğer yoksa, yeni bir tane oluşturacağız (POST gibi davranırız)
        serializer = EventStatisticSerializer(data=data)
        status_code = status.HTTP_201_CREATED # Oluşturma başarılıysa 201 Created

    if serializer.is_valid():
        try:
            serializer.save()
            return Response(serializer.data, status=status_code)
        except Exception as e: # Veritabanına kaydetme sırasında olası hatalar (validasyon dışı)
            print(f"HATA: EventStatistic kaydedilirken/güncellenirken beklenmedik bir hata oluştu: {e}")
            traceback.print_exc()
            return Response(
                {"error": f"Veri kaydedilirken/güncellenirken beklenmedik bir hata oluştu: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    else:
        print(f"HATA: Serializer doğrulama hatası: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Event Statistic Retrieval (Yeni Endpoint)
@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_event_statistic(request, event_id):
    try:
        event = Event.objects.get(eventId=event_id)
    except Event.DoesNotExist:
        return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)

    # Etkinlik sahipliği kontrolü
    if event.event_owner != request.user:
        return Response(
            {"error": "You are not the owner of this event"},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        statistic = EventStatistic.objects.get(event=event)
        serializer = EventStatisticSerializer(statistic)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except EventStatistic.DoesNotExist:
        return Response(
            {"error": "Statistics not found for this event"},
            status=status.HTTP_404_NOT_FOUND
        )

# Event Statistic Update
@api_view(["PUT"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_event_statistic(request, event_id):
    try:
        event = Event.objects.get(eventId=event_id)
    except Event.DoesNotExist:
        return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        event_statistics = EventStatistic.objects.get(event=event)
    except EventStatistic.DoesNotExist:
        return Response(
            {"error": "EventStatistic not found"}, status=status.HTTP_404_NOT_FOUND
        )

    data = request.data.copy()
    data["event"] = event.id

    serializer = EventStatisticSerializer(instance=event_statistics, data=data)
    if serializer.is_valid():
        event_statistics.delete()

        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# PHOTO VIEWS


class PhotoCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        photos_data = request.FILES.getlist("path")
        event_id = request.data.get("event")
        event = Event.objects.filter(eventId=event_id, event_owner=request.user).first()

        if event is None:
            return Response(
                {"detail": "Event does not exist"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializers = [
            PhotoSerializer(data={"event": event_id, "path": photo})
            for photo in photos_data
        ]

        for serializer in serializers:
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        photo_instances = [
            Photo(event=event, path=serializer.validated_data["path"])
            for serializer in serializers
        ]
        Photo.objects.bulk_create(photo_instances)

        response_serializer = PhotoSerializer(photo_instances, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class PhotoDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Photo.objects.all()
    serializer_class = PhotoSerializer
    lookup_field = "photoId"


class EventPhotosListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PhotoSerializer

    def get_queryset(self):
        event_id = self.kwargs["eventId"]
        event = Event.objects.filter(
            eventId=event_id, event_owner=self.request.user
        ).first()
        if event:
            return Photo.objects.filter(event=event)
        else:
            return Photo.objects.none()

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if (
            not queryset.exists()
            and not Event.objects.filter(
                eventId=self.kwargs["eventId"], event_owner=self.request.user
            ).exists()
        ):
            return Response(
                {"detail": "Event does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class PhotoDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Photo.objects.all()
    serializer_class = PhotoSerializer
    lookup_field = "photoId"

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.event.event_owner == request.user:
            self.perform_destroy(instance)
            return Response(
                {"detail": "Photo has been deleted successfully"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"detail": "You do not have permission to delete this photo."},
                status=status.HTTP_403_FORBIDDEN,
            )