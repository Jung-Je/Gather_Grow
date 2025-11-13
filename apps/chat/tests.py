from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat.models import ChatMessage
from apps.gatherings.models import Category, Gathering, GatheringMember
from apps.users.models import User


class ChatMessageAPITestCase(TestCase):
    """채팅 메시지 API 테스트"""

    def setUp(self):
        """테스트 데이터 설정"""
        # 사용자 생성
        self.user1 = User.objects.create_user(email="user1@test.com", username="user1", password="testpass123!")
        self.user2 = User.objects.create_user(email="user2@test.com", username="user2", password="testpass123!")
        self.user3 = User.objects.create_user(email="user3@test.com", username="user3", password="testpass123!")

        # 카테고리 생성
        self.category = Category.objects.create(name="테스트 카테고리")

        # 모임 생성 (user1이 모임장)
        self.gathering = Gathering.objects.create(
            user=self.user1,
            category=self.category,
            type=Gathering.GatheringType.STUDY,
            title="테스트 스터디",
            description="테스트용 스터디입니다",
            max_members=5,
            recruitment_end="2024-12-31",
            start_date="2025-01-01",
            study_type=Gathering.StudyType.ONLINE,
            target_level=Gathering.TargetLevel.ALL,
        )

        # user2를 승인된 멤버로 추가
        self.member = GatheringMember.objects.create(
            user=self.user2,
            gathering=self.gathering,
            role=GatheringMember.MemberRole.PARTICIPANT,
            status=GatheringMember.MemberStatus.APPROVED,
        )

        self.client = APIClient()

    def test_message_list_unauthorized(self):
        """인증 없이 메시지 조회 실패"""
        url = reverse("chat:message-list", kwargs={"gathering_id": self.gathering.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_message_list_not_member(self):
        """모임 멤버가 아닌 사용자 접근 실패"""
        self.client.force_authenticate(user=self.user3)
        url = reverse("chat:message-list", kwargs={"gathering_id": self.gathering.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_message_list_success_as_leader(self):
        """모임장으로 메시지 목록 조회 성공"""
        self.client.force_authenticate(user=self.user1)
        url = reverse("chat:message-list", kwargs={"gathering_id": self.gathering.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_message_list_success_as_member(self):
        """승인된 멤버로 메시지 목록 조회 성공"""
        self.client.force_authenticate(user=self.user2)
        url = reverse("chat:message-list", kwargs={"gathering_id": self.gathering.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_send_text_message_success(self):
        """텍스트 메시지 전송 성공"""
        self.client.force_authenticate(user=self.user1)
        url = reverse("chat:message-list", kwargs={"gathering_id": self.gathering.id})

        data = {"gathering": self.gathering.id, "message": "안녕하세요!"}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ChatMessage.objects.count(), 1)

        message = ChatMessage.objects.first()
        self.assertEqual(message.user, self.user1)
        self.assertEqual(message.gathering, self.gathering)
        self.assertEqual(message.message, "안녕하세요!")
        self.assertFalse(message.image)  # ImageField는 빈 값일 때 False로 평가됨

    def test_send_message_without_content(self):
        """내용 없이 메시지 전송 실패"""
        self.client.force_authenticate(user=self.user1)
        url = reverse("chat:message-list", kwargs={"gathering_id": self.gathering.id})

        data = {"gathering": self.gathering.id}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_send_message_not_member(self):
        """모임 멤버가 아닌 사용자 메시지 전송 실패"""
        self.client.force_authenticate(user=self.user3)
        url = reverse("chat:message-list", kwargs={"gathering_id": self.gathering.id})

        data = {"gathering": self.gathering.id, "message": "안녕하세요!"}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_message_list_pagination(self):
        """메시지 목록 페이지네이션"""
        self.client.force_authenticate(user=self.user1)

        # 100개의 메시지 생성
        for i in range(100):
            ChatMessage.objects.create(gathering=self.gathering, user=self.user1, message=f"메시지 {i}")

        url = reverse("chat:message-list", kwargs={"gathering_id": self.gathering.id})

        # 첫 페이지
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 50)  # 기본 페이지 크기

        # 두 번째 페이지
        response = self.client.get(url, {"page": 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 50)

    def test_message_ordering(self):
        """메시지 최신순 정렬 확인"""
        self.client.force_authenticate(user=self.user1)

        # 메시지 3개 생성
        msg1 = ChatMessage.objects.create(gathering=self.gathering, user=self.user1, message="첫 번째 메시지")
        msg2 = ChatMessage.objects.create(gathering=self.gathering, user=self.user1, message="두 번째 메시지")
        msg3 = ChatMessage.objects.create(gathering=self.gathering, user=self.user1, message="세 번째 메시지")

        url = reverse("chat:message-list", kwargs={"gathering_id": self.gathering.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        messages = response.data["results"]

        # 최신순이므로 msg3, msg2, msg1 순서
        self.assertEqual(messages[0]["id"], msg3.id)
        self.assertEqual(messages[1]["id"], msg2.id)
        self.assertEqual(messages[2]["id"], msg1.id)

    def test_message_includes_user_info(self):
        """메시지에 사용자 정보 포함 확인"""
        self.client.force_authenticate(user=self.user1)

        ChatMessage.objects.create(gathering=self.gathering, user=self.user1, message="테스트 메시지")

        url = reverse("chat:message-list", kwargs={"gathering_id": self.gathering.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        message = response.data["results"][0]

        self.assertEqual(message["username"], "user1")
        self.assertIn("user_profile_image", message)
        self.assertIn("has_image", message)
        self.assertIn("has_text", message)
