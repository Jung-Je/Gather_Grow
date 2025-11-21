from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.communitys.models import Answer, Question
from apps.gatherings.models import Category

User = get_user_model()


class QuestionAPITestCase(APITestCase):
    """Q&A 질문 API 테스트"""

    def setUp(self):
        """테스트 데이터 준비"""
        # 사용자 생성
        self.user1 = User.objects.create_user(
            email="user1@test.com",
            password="User1234!@",
            username="사용자1",
        )

        self.user2 = User.objects.create_user(
            email="user2@test.com",
            password="User1234!@",
            username="사용자2",
        )

        # 카테고리 생성
        self.category = Category.objects.create(
            name="Python",
            description="파이썬 관련 질문",
        )

        # 질문 생성
        self.question = Question.objects.create(
            user=self.user1,
            category=self.category,
            title="Django ORM 질문",
            content="Django ORM에서 N+1 문제를 해결하는 방법이 궁금합니다.",
        )

    def test_question_list(self):
        """질문 목록 조회 테스트 (페이지네이션)"""
        url = "/api/v1/communitys/questions/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(len(response.data["data"]["results"]), 1)

    def test_question_list_filter_by_category(self):
        """카테고리별 필터링 테스트 (페이지네이션)"""
        # 다른 카테고리 질문 생성
        category2 = Category.objects.create(name="JavaScript")
        Question.objects.create(
            user=self.user1,
            category=category2,
            title="React 질문",
            content="React Hooks 사용법",
        )

        url = f"/api/v1/communitys/questions/?category={self.category.id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(response.data["data"]["results"][0]["title"], "Django ORM 질문")

    def test_question_list_filter_by_solved(self):
        """답변 여부 필터링 테스트 (페이지네이션)"""
        # 해결된 질문 생성
        Question.objects.create(
            user=self.user1,
            category=self.category,
            title="해결된 질문",
            content="내용",
            is_solved=True,
        )

        # 미해결 질문만 조회
        url = "/api/v1/communitys/questions/?is_solved=false"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)

        # 해결된 질문만 조회
        url = "/api/v1/communitys/questions/?is_solved=true"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)

    def test_question_list_search(self):
        """질문 검색 테스트 (페이지네이션)"""
        url = "/api/v1/communitys/questions/?search=Django"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertIn("Django", response.data["data"]["results"][0]["title"])

    def test_question_list_invalid_category(self):
        """잘못된 카테고리 ID로 필터링 실패 테스트"""
        url = "/api/v1/communitys/questions/?category=invalid"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("잘못된 카테고리 ID", response.data["message"])

    def test_question_detail(self):
        """질문 상세 조회 테스트"""
        url = f"/api/v1/communitys/questions/{self.question.id}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["title"], "Django ORM 질문")
        self.assertIn("view_count", response.data["data"])

    def test_question_detail_increments_view_count(self):
        """질문 조회 시 조회수 증가 테스트"""
        initial_view_count = self.question.view_count
        url = f"/api/v1/communitys/questions/{self.question.id}/"

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.question.refresh_from_db()
        self.assertEqual(self.question.view_count, initial_view_count + 1)

    def test_question_detail_not_found(self):
        """존재하지 않는 질문 조회 실패 테스트"""
        url = "/api/v1/communitys/questions/99999/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_question_create_success(self):
        """질문 생성 성공 테스트"""
        self.client.force_authenticate(user=self.user1)
        url = "/api/v1/communitys/questions/"
        data = {
            "category": self.category.id,
            "title": "새로운 질문",
            "content": "질문 내용입니다. 최소 10자 이상이어야 합니다.",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["title"], "새로운 질문")
        self.assertTrue(Question.objects.filter(title="새로운 질문").exists())

    def test_question_create_without_auth(self):
        """인증 없이 질문 생성 실패 테스트"""
        url = "/api/v1/communitys/questions/"
        data = {
            "category": self.category.id,
            "title": "새로운 질문",
            "content": "질문 내용입니다.",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_question_create_invalid_data(self):
        """유효하지 않은 데이터로 질문 생성 실패 테스트"""
        self.client.force_authenticate(user=self.user1)
        url = "/api/v1/communitys/questions/"
        data = {
            "category": self.category.id,
            # title 누락
            "content": "질문 내용입니다.",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_question_update_by_author(self):
        """질문 수정 테스트 (작성자)"""
        self.client.force_authenticate(user=self.user1)
        url = f"/api/v1/communitys/questions/{self.question.id}/"
        data = {
            "title": "수정된 제목",
            "content": "수정된 내용입니다. 최소 10자 이상이어야 합니다.",
        }
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["title"], "수정된 제목")

        # DB 확인
        self.question.refresh_from_db()
        self.assertEqual(self.question.title, "수정된 제목")
        self.assertEqual(self.question.content, "수정된 내용입니다. 최소 10자 이상이어야 합니다.")

    def test_question_update_by_non_author_fail(self):
        """질문 수정 실패 테스트 (작성자 아님)"""
        self.client.force_authenticate(user=self.user2)
        url = f"/api/v1/communitys/questions/{self.question.id}/"
        data = {"title": "수정 시도"}
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_question_delete_by_author(self):
        """질문 삭제 테스트 (작성자)"""
        self.client.force_authenticate(user=self.user1)
        url = f"/api/v1/communitys/questions/{self.question.id}/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Question.objects.filter(id=self.question.id).exists())

    def test_question_delete_by_non_author_fail(self):
        """질문 삭제 실패 테스트 (작성자 아님)"""
        self.client.force_authenticate(user=self.user2)
        url = f"/api/v1/communitys/questions/{self.question.id}/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_question_mark_as_solved(self):
        """질문 해결 표시 테스트 (작성자)"""
        self.client.force_authenticate(user=self.user1)
        url = f"/api/v1/communitys/questions/{self.question.id}/solved/"
        response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.question.refresh_from_db()
        self.assertTrue(self.question.is_solved)

    def test_question_mark_as_unsolved(self):
        """질문 미해결 표시 테스트 (작성자)"""
        self.question.is_solved = True
        self.question.save()

        self.client.force_authenticate(user=self.user1)
        url = f"/api/v1/communitys/questions/{self.question.id}/solved/"
        response = self.client.patch(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.question.refresh_from_db()
        self.assertFalse(self.question.is_solved)

    def test_my_question_list(self):
        """내 질문 목록 조회 테스트 (페이지네이션)"""
        # user2의 질문 생성
        Question.objects.create(
            user=self.user2,
            category=self.category,
            title="user2의 질문",
            content="내용",
        )

        self.client.force_authenticate(user=self.user1)
        url = "/api/v1/communitys/questions/me/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(response.data["data"]["results"][0]["username"], "사용자1")


class AnswerAPITestCase(APITestCase):
    """Q&A 답변 API 테스트"""

    def setUp(self):
        """테스트 데이터 준비"""
        # 사용자 생성
        self.user1 = User.objects.create_user(
            email="user1@test.com",
            password="User1234!@",
            username="사용자1",
        )

        self.user2 = User.objects.create_user(
            email="user2@test.com",
            password="User1234!@",
            username="사용자2",
        )

        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="Admin1234!@",
            username="관리자",
            role="admin",
        )
        self.admin_user.is_staff = True
        self.admin_user.save()

        # 카테고리 생성
        self.category = Category.objects.create(
            name="Python",
            description="파이썬 관련 질문",
        )

        # 질문 생성
        self.question = Question.objects.create(
            user=self.user1,
            category=self.category,
            title="Django ORM 질문",
            content="Django ORM에서 N+1 문제를 해결하는 방법이 궁금합니다.",
        )

        # 답변 생성
        self.answer = Answer.objects.create(
            question=self.question,
            user=self.user2,
            content="select_related()와 prefetch_related()를 사용하면 됩니다.",
        )

    def test_answer_list(self):
        """답변 목록 조회 테스트 (페이지네이션)"""
        url = f"/api/v1/communitys/questions/{self.question.id}/answers/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(len(response.data["data"]["results"]), 1)

    def test_answer_list_question_not_found(self):
        """존재하지 않는 질문의 답변 목록 조회 실패 테스트"""
        url = "/api/v1/communitys/questions/99999/answers/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_answer_create_success(self):
        """답변 생성 성공 테스트"""
        self.client.force_authenticate(user=self.user2)
        url = f"/api/v1/communitys/questions/{self.question.id}/answers/"
        data = {
            "content": "새로운 답변입니다.",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["content"], "새로운 답변입니다.")
        self.assertTrue(Answer.objects.filter(content="새로운 답변입니다.").exists())

    def test_answer_create_without_auth(self):
        """인증 없이 답변 생성 실패 테스트"""
        url = f"/api/v1/communitys/questions/{self.question.id}/answers/"
        data = {
            "content": "새로운 답변입니다.",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_answer_create_on_solved_question_fail(self):
        """해결된 질문에 답변 작성 실패 테스트"""
        self.question.is_solved = True
        self.question.save()

        self.client.force_authenticate(user=self.user2)
        url = f"/api/v1/communitys/questions/{self.question.id}/answers/"
        data = {
            "content": "새로운 답변입니다. 최소 10자 이상이어야 합니다.",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_answer_create_question_not_found(self):
        """존재하지 않는 질문에 답변 작성 실패 테스트"""
        self.client.force_authenticate(user=self.user2)
        url = "/api/v1/communitys/questions/99999/answers/"
        data = {
            "content": "새로운 답변입니다.",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_answer_detail(self):
        """답변 상세 조회 테스트"""
        url = f"/api/v1/communitys/answers/{self.answer.id}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["content"], self.answer.content)

    def test_answer_detail_not_found(self):
        """존재하지 않는 답변 조회 실패 테스트"""
        url = "/api/v1/communitys/answers/99999/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_answer_update_by_author(self):
        """답변 수정 테스트 (작성자)"""
        self.client.force_authenticate(user=self.user2)
        url = f"/api/v1/communitys/answers/{self.answer.id}/"
        data = {
            "content": "수정된 답변 내용입니다.",
        }
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["content"], "수정된 답변 내용입니다.")

        # DB 확인
        self.answer.refresh_from_db()
        self.assertEqual(self.answer.content, "수정된 답변 내용입니다.")

    def test_answer_update_by_non_author_fail(self):
        """답변 수정 실패 테스트 (작성자 아님)"""
        self.client.force_authenticate(user=self.user1)
        url = f"/api/v1/communitys/answers/{self.answer.id}/"
        data = {
            "content": "수정 시도",
        }
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_answer_delete_by_author(self):
        """답변 삭제 테스트 (작성자)"""
        self.client.force_authenticate(user=self.user2)
        url = f"/api/v1/communitys/answers/{self.answer.id}/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Answer.objects.filter(id=self.answer.id).exists())

    def test_answer_delete_by_question_author(self):
        """답변 삭제 테스트 (질문 작성자)"""
        self.client.force_authenticate(user=self.user1)
        url = f"/api/v1/communitys/answers/{self.answer.id}/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Answer.objects.filter(id=self.answer.id).exists())

    def test_answer_delete_by_non_author_fail(self):
        """답변 삭제 실패 테스트 (작성자도 아니고 질문 작성자도 아님)"""
        user3 = User.objects.create_user(
            email="user3@test.com",
            password="User1234!@",
            username="사용자3",
        )

        self.client.force_authenticate(user=user3)
        url = f"/api/v1/communitys/answers/{self.answer.id}/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_answer_is_author_admin_property(self):
        """관리자 답변 여부 확인 테스트"""
        # 관리자 답변 생성
        admin_answer = Answer.objects.create(
            question=self.question,
            user=self.admin_user,
            content="관리자 답변입니다.",
        )

        self.assertTrue(admin_answer.is_author_admin)
        self.assertFalse(self.answer.is_author_admin)

    def test_my_answer_list(self):
        """내 답변 목록 조회 테스트 (페이지네이션)"""
        # user1의 답변 생성
        Answer.objects.create(
            question=self.question,
            user=self.user1,
            content="user1의 답변",
        )

        self.client.force_authenticate(user=self.user2)
        url = "/api/v1/communitys/answers/me/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(response.data["data"]["results"][0]["username"], "사용자2")
