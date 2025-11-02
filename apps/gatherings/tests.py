from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.gatherings.models import Category, Gathering, GatheringMember

User = get_user_model()


class CategoryAPITestCase(APITestCase):
    """카테고리 API 테스트"""

    def setUp(self):
        """테스트 데이터 준비"""
        # 관리자 사용자 생성 (is_staff=True 필요)
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="Admin1234!@",
            username="관리자",
            role="admin",
        )
        self.admin_user.is_staff = True
        self.admin_user.save()

        # 일반 사용자 생성
        self.normal_user = User.objects.create_user(
            email="user@test.com",
            password="User1234!@",
            username="일반사용자",
        )

        # 부모 카테고리 생성
        self.parent_category = Category.objects.create(
            name="프로그래밍",
            description="프로그래밍 관련 카테고리",
        )

        # 자식 카테고리 생성
        self.child_category = Category.objects.create(
            name="Python",
            description="파이썬 프로그래밍",
            parent=self.parent_category,
        )

    def test_category_list(self):
        """카테고리 목록 조회 테스트"""
        url = "/api/v1/gatherings/categories/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)  # 부모 1개 + 자식 1개

    def test_category_list_hierarchical(self):
        """계층 구조 카테고리 목록 조회 테스트"""
        url = "/api/v1/gatherings/categories/?hierarchical=true"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(len(data), 1)  # 부모 카테고리만
        self.assertIn("children", data[0])
        self.assertEqual(len(data[0]["children"]), 1)  # 자식 1개

    def test_parent_category_list(self):
        """부모 카테고리만 조회 테스트"""
        url = "/api/v1/gatherings/categories/parents/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)  # 부모 카테고리만
        self.assertEqual(response.data["data"][0]["name"], "프로그래밍")

    def test_child_category_list(self):
        """자식 카테고리 조회 테스트"""
        url = f"/api/v1/gatherings/categories/{self.parent_category.id}/children/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)  # 자식 1개
        self.assertEqual(response.data["data"][0]["name"], "Python")

    def test_category_detail(self):
        """카테고리 상세 조회 테스트"""
        url = f"/api/v1/gatherings/categories/{self.parent_category.id}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["name"], "프로그래밍")
        self.assertIn("total_gatherings", response.data["data"])
        self.assertIn("recruiting_gatherings", response.data["data"])

    def test_category_create_success(self):
        """카테고리 생성 성공 테스트 (관리자)"""
        self.client.force_authenticate(user=self.admin_user)
        url = "/api/v1/gatherings/categories/manage/"
        data = {
            "name": "디자인",
            "description": "디자인 관련 카테고리",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["name"], "디자인")
        self.assertTrue(Category.objects.filter(name="디자인").exists())

    def test_category_create_with_parent(self):
        """자식 카테고리 생성 테스트"""
        self.client.force_authenticate(user=self.admin_user)
        url = "/api/v1/gatherings/categories/manage/"
        data = {
            "name": "JavaScript",
            "description": "자바스크립트",
            "parent": self.parent_category.id,
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["parent"], self.parent_category.id)

    def test_category_create_unauthorized(self):
        """카테고리 생성 권한 없음 테스트 (일반 사용자)"""
        self.client.force_authenticate(user=self.normal_user)
        url = "/api/v1/gatherings/categories/manage/"
        data = {
            "name": "테스트",
            "description": "테스트",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_category_update(self):
        """카테고리 수정 테스트"""
        self.client.force_authenticate(user=self.admin_user)
        url = f"/api/v1/gatherings/categories/{self.parent_category.id}/manage/"
        data = {
            "name": "프로그래밍 (수정됨)",
            "description": "수정된 설명",
        }
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["name"], "프로그래밍 (수정됨)")

        # DB 확인
        self.parent_category.refresh_from_db()
        self.assertEqual(self.parent_category.name, "프로그래밍 (수정됨)")

    def test_category_deactivate(self):
        """카테고리 비활성화 테스트"""
        self.client.force_authenticate(user=self.admin_user)

        # 모임이 없는 카테고리 생성
        empty_category = Category.objects.create(name="비어있음")

        url = f"/api/v1/gatherings/categories/{empty_category.id}/manage/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # DB 확인
        empty_category.refresh_from_db()
        self.assertFalse(empty_category.is_active)

    def test_category_delete_with_gatherings_fail(self):
        """진행 중인 모임이 있는 카테고리 삭제 실패 테스트"""
        self.client.force_authenticate(user=self.admin_user)

        # 모임 생성
        Gathering.objects.create(
            user=self.admin_user,
            category=self.parent_category,
            type="study",
            title="테스트 모임",
            description="설명",
            max_members=5,
            recruitment_end=date.today() + timedelta(days=7),
            start_date=date.today() + timedelta(days=14),
            study_type="online",
            target_level="all",
            status=Gathering.GatheringStatus.RECRUITING,
        )

        url = f"/api/v1/gatherings/categories/{self.parent_category.id}/manage/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class GatheringAPITestCase(APITestCase):
    """모임 API 테스트"""

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
            description="파이썬",
        )

        # 모임 생성
        self.gathering = Gathering.objects.create(
            user=self.user1,
            category=self.category,
            type="study",
            title="Django 스터디",
            description="DRF 스터디입니다.",
            max_members=5,
            recruitment_end=date.today() + timedelta(days=7),
            start_date=date.today() + timedelta(days=14),
            study_type="online",
            target_level="intermediate",
            status=Gathering.GatheringStatus.RECRUITING,
        )

        # 모임장을 멤버로 추가
        GatheringMember.objects.create(
            user=self.user1,
            gathering=self.gathering,
            role=GatheringMember.MemberRole.LEADER,
            status=GatheringMember.MemberStatus.APPROVED,
        )

    def test_gathering_list(self):
        """모임 목록 조회 테스트 (페이지네이션)"""
        url = "/api/v1/gatherings/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(len(response.data["data"]["results"]), 1)

    def test_gathering_list_filter_by_type(self):
        """모임 타입 필터링 테스트 (페이지네이션)"""
        # 프로젝트 모임 생성
        Gathering.objects.create(
            user=self.user1,
            category=self.category,
            type="project",
            title="프로젝트 모임",
            description="프로젝트",
            max_members=4,
            recruitment_end=date.today() + timedelta(days=7),
            start_date=date.today() + timedelta(days=14),
            study_type="offline",
            location="서울",
            target_level="beginner",
            required_skills="Python",
        )

        url = "/api/v1/gatherings/?type=study"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(len(response.data["data"]["results"]), 1)
        self.assertEqual(response.data["data"]["results"][0]["type"], "study")

    def test_gathering_list_search(self):
        """모임 검색 테스트 (페이지네이션)"""
        url = "/api/v1/gatherings/?search=Django"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(len(response.data["data"]["results"]), 1)
        self.assertIn("Django", response.data["data"]["results"][0]["title"])

    def test_gathering_list_invalid_filter(self):
        """모임 목록 조회 시 잘못된 필터 값 테스트"""
        # 잘못된 type
        url = "/api/v1/gatherings/?type=invalid"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("잘못된 모임 유형", response.data["message"])

        # 잘못된 status
        url = "/api/v1/gatherings/?status=invalid"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("잘못된 모집 상태", response.data["message"])

        # 잘못된 study_type
        url = "/api/v1/gatherings/?study_type=invalid"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("잘못된 진행 방식", response.data["message"])

        # 잘못된 target_level
        url = "/api/v1/gatherings/?target_level=invalid"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("잘못된 대상 수준", response.data["message"])

    def test_gathering_detail(self):
        """모임 상세 조회 테스트"""
        url = f"/api/v1/gatherings/{self.gathering.id}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["title"], "Django 스터디")
        self.assertEqual(response.data["data"]["max_members"], 5)

    def test_gathering_create_success(self):
        """모임 생성 성공 테스트"""
        self.client.force_authenticate(user=self.user1)
        url = "/api/v1/gatherings/"
        data = {
            "category": self.category.id,
            "type": "study",
            "title": "새로운 스터디",
            "description": "스터디 설명",
            "max_members": 6,
            "recruitment_end": str(date.today() + timedelta(days=10)),
            "start_date": str(date.today() + timedelta(days=20)),
            "end_date": str(date.today() + timedelta(days=50)),
            "meeting_schedule": "매주 수요일",
            "study_type": "online",
            "target_level": "all",
            "has_cost": False,
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["title"], "새로운 스터디")

        # 모임장이 자동으로 멤버에 추가되었는지 확인
        new_gathering_id = response.data["data"]["id"]
        self.assertTrue(
            GatheringMember.objects.filter(
                gathering_id=new_gathering_id,
                user=self.user1,
                role=GatheringMember.MemberRole.LEADER,
            ).exists()
        )

    def test_gathering_create_validation_fail(self):
        """모임 생성 검증 실패 테스트 (시작일이 모집 마감일보다 이전)"""
        self.client.force_authenticate(user=self.user1)
        url = "/api/v1/gatherings/"
        data = {
            "category": self.category.id,
            "type": "study",
            "title": "잘못된 모임",
            "description": "설명",
            "max_members": 5,
            "recruitment_end": str(date.today() + timedelta(days=20)),
            "start_date": str(date.today() + timedelta(days=10)),  # 모집 마감일보다 이전
            "study_type": "online",
            "target_level": "all",
            "has_cost": False,
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_gathering_update_by_leader(self):
        """모임 수정 테스트 (모임장)"""
        self.client.force_authenticate(user=self.user1)
        url = f"/api/v1/gatherings/{self.gathering.id}/"
        data = {
            "description": "수정된 설명",
            "meeting_schedule": "매주 목요일",
        }
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["description"], "수정된 설명")

        # DB 확인
        self.gathering.refresh_from_db()
        self.assertEqual(self.gathering.description, "수정된 설명")

    def test_gathering_update_by_non_leader_fail(self):
        """모임 수정 실패 테스트 (모임장 아님)"""
        self.client.force_authenticate(user=self.user2)
        url = f"/api/v1/gatherings/{self.gathering.id}/"
        data = {"description": "수정 시도"}
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_gathering_status_change(self):
        """모임 상태 변경 테스트"""
        self.client.force_authenticate(user=self.user1)
        url = f"/api/v1/gatherings/{self.gathering.id}/status/"
        data = {"status": "recruitment_complete"}
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["status"], "recruitment_complete")

        # DB 확인
        self.gathering.refresh_from_db()
        self.assertEqual(self.gathering.status, Gathering.GatheringStatus.RECRUITMENT_COMPLETE)

    def test_gathering_delete_by_leader(self):
        """모임 삭제 테스트 (모임장, 멤버 1명)"""
        self.client.force_authenticate(user=self.user1)
        url = f"/api/v1/gatherings/{self.gathering.id}/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Gathering.objects.filter(id=self.gathering.id).exists())

    def test_gathering_statistics(self):
        """모임 통계 조회 테스트"""
        url = f"/api/v1/gatherings/{self.gathering.id}/statistics/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertIn("max_members", data)
        self.assertIn("current_members", data)
        self.assertIn("remaining_seats", data)
        self.assertIn("is_full", data)

    def test_my_gathering_list(self):
        """내 모임 목록 조회 테스트 (페이지네이션)"""
        self.client.force_authenticate(user=self.user1)
        url = "/api/v1/gatherings/my/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(len(response.data["data"]["results"]), 1)


class MemberAPITestCase(APITestCase):
    """멤버 API 테스트"""

    def setUp(self):
        """테스트 데이터 준비"""
        # 사용자 생성
        self.leader = User.objects.create_user(
            email="leader@test.com",
            password="User1234!@",
            username="모임장",
        )

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
        self.category = Category.objects.create(name="Python")

        # 모임 생성
        self.gathering = Gathering.objects.create(
            user=self.leader,
            category=self.category,
            type="study",
            title="테스트 스터디",
            description="설명",
            max_members=5,
            recruitment_end=date.today() + timedelta(days=7),
            start_date=date.today() + timedelta(days=14),
            study_type="online",
            target_level="all",
            status=Gathering.GatheringStatus.RECRUITING,
        )

        # 모임장 멤버
        self.leader_member = GatheringMember.objects.create(
            user=self.leader,
            gathering=self.gathering,
            role=GatheringMember.MemberRole.LEADER,
            status=GatheringMember.MemberStatus.APPROVED,
        )

    def test_member_join_success(self):
        """모임 가입 신청 성공 테스트"""
        self.client.force_authenticate(user=self.user1)
        url = f"/api/v1/gatherings/{self.gathering.id}/join/"
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["status"], "pending")

        # DB 확인
        self.assertTrue(
            GatheringMember.objects.filter(
                user=self.user1,
                gathering=self.gathering,
                status=GatheringMember.MemberStatus.PENDING,
            ).exists()
        )

    def test_member_join_duplicate_fail(self):
        """중복 가입 신청 실패 테스트"""
        self.client.force_authenticate(user=self.user1)
        url = f"/api/v1/gatherings/{self.gathering.id}/join/"

        # 첫 번째 가입
        self.client.post(url)

        # 두 번째 가입 시도
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_member_join_full_gathering_fail(self):
        """정원 마감 모임 가입 실패 테스트"""
        # 모임을 정원 마감 상태로 변경
        self.gathering.max_members = 1
        self.gathering.save()

        self.client.force_authenticate(user=self.user1)
        url = f"/api/v1/gatherings/{self.gathering.id}/join/"
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_member_list(self):
        """멤버 목록 조회 테스트 (승인된 멤버만, 페이지네이션)"""
        # 승인된 멤버 추가
        GatheringMember.objects.create(
            user=self.user1,
            gathering=self.gathering,
            status=GatheringMember.MemberStatus.APPROVED,
        )

        # 대기 중인 멤버 추가 (목록에 안 나와야 함)
        GatheringMember.objects.create(
            user=self.user2,
            gathering=self.gathering,
            status=GatheringMember.MemberStatus.PENDING,
        )

        url = f"/api/v1/gatherings/{self.gathering.id}/members/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 2)  # 모임장 + 승인된 user1만
        self.assertEqual(len(response.data["data"]["results"]), 2)

    def test_pending_member_list(self):
        """승인 대기 멤버 목록 조회 테스트 (모임장, 페이지네이션)"""
        # 대기 중인 멤버 추가
        GatheringMember.objects.create(
            user=self.user1,
            gathering=self.gathering,
            status=GatheringMember.MemberStatus.PENDING,
        )

        self.client.force_authenticate(user=self.leader)
        url = f"/api/v1/gatherings/{self.gathering.id}/members/pending/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(len(response.data["data"]["results"]), 1)
        self.assertEqual(response.data["data"]["results"][0]["status"], "pending")

    def test_pending_member_list_unauthorized(self):
        """승인 대기 멤버 목록 조회 실패 테스트 (모임장 아님)"""
        # 대기 중인 멤버 추가
        GatheringMember.objects.create(
            user=self.user1,
            gathering=self.gathering,
            status=GatheringMember.MemberStatus.PENDING,
        )

        # 일반 사용자로 조회 시도
        self.client.force_authenticate(user=self.user2)
        url = f"/api/v1/gatherings/{self.gathering.id}/members/pending/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_approval_by_leader(self):
        """멤버 승인 테스트 (모임장)"""
        # 대기 중인 멤버 생성
        member = GatheringMember.objects.create(
            user=self.user1,
            gathering=self.gathering,
            status=GatheringMember.MemberStatus.PENDING,
        )

        self.client.force_authenticate(user=self.leader)
        url = f"/api/v1/gatherings/members/{member.id}/approval/"
        data = {"action": "approve"}
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["status"], "approved")

        # DB 확인
        member.refresh_from_db()
        self.assertEqual(member.status, GatheringMember.MemberStatus.APPROVED)

        # current_members 증가 확인
        self.gathering.refresh_from_db()
        self.assertEqual(self.gathering.current_members, 2)

    def test_member_approval_full_gathering_fail(self):
        """정원 마감 시 멤버 승인 실패 테스트 (race condition 방지)"""
        # 모임을 정원 마감 상태로 변경
        self.gathering.current_members = self.gathering.max_members
        self.gathering.save()

        # 대기 중인 멤버 생성
        member = GatheringMember.objects.create(
            user=self.user1,
            gathering=self.gathering,
            status=GatheringMember.MemberStatus.PENDING,
        )

        self.client.force_authenticate(user=self.leader)
        url = f"/api/v1/gatherings/members/{member.id}/approval/"
        data = {"action": "approve"}
        response = self.client.patch(url, data, format="json")

        # 정원 초과로 승인 실패해야 함
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("정원", response.data["message"])

    def test_member_rejection_by_leader(self):
        """멤버 거절 테스트 (모임장)"""
        # 대기 중인 멤버 생성
        member = GatheringMember.objects.create(
            user=self.user1,
            gathering=self.gathering,
            status=GatheringMember.MemberStatus.PENDING,
        )

        self.client.force_authenticate(user=self.leader)
        url = f"/api/v1/gatherings/members/{member.id}/approval/"
        data = {"action": "reject"}
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["status"], "rejected")

        # DB 확인
        member.refresh_from_db()
        self.assertEqual(member.status, GatheringMember.MemberStatus.REJECTED)

    def test_member_approval_by_non_leader_fail(self):
        """멤버 승인 실패 테스트 (모임장 아님)"""
        # 대기 중인 멤버 생성
        member = GatheringMember.objects.create(
            user=self.user1,
            gathering=self.gathering,
            status=GatheringMember.MemberStatus.PENDING,
        )

        self.client.force_authenticate(user=self.user2)
        url = f"/api/v1/gatherings/members/{member.id}/approval/"
        data = {"action": "approve"}
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_member_cancel_join(self):
        """가입 신청 취소 테스트"""
        # 대기 중인 멤버 생성
        GatheringMember.objects.create(
            user=self.user1,
            gathering=self.gathering,
            status=GatheringMember.MemberStatus.PENDING,
        )

        self.client.force_authenticate(user=self.user1)
        url = f"/api/v1/gatherings/{self.gathering.id}/join/cancel/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # DB 확인 (삭제됨)
        self.assertFalse(
            GatheringMember.objects.filter(
                user=self.user1,
                gathering=self.gathering,
            ).exists()
        )

    def test_member_leave(self):
        """모임 탈퇴 테스트"""
        # 승인된 멤버 생성
        member = GatheringMember.objects.create(
            user=self.user1,
            gathering=self.gathering,
            status=GatheringMember.MemberStatus.APPROVED,
        )
        self.gathering.current_members = 2
        self.gathering.save()

        self.client.force_authenticate(user=self.user1)
        url = f"/api/v1/gatherings/{self.gathering.id}/leave/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # DB 확인
        member.refresh_from_db()
        self.assertFalse(member.is_active)

        # current_members 감소 확인
        self.gathering.refresh_from_db()
        self.assertEqual(self.gathering.current_members, 1)

    def test_leader_leave_fail(self):
        """모임장 탈퇴 실패 테스트"""
        self.client.force_authenticate(user=self.leader)
        url = f"/api/v1/gatherings/{self.gathering.id}/leave/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_member_remove_by_leader(self):
        """멤버 강제 탈퇴 테스트 (모임장)"""
        # 승인된 멤버 생성
        member = GatheringMember.objects.create(
            user=self.user1,
            gathering=self.gathering,
            status=GatheringMember.MemberStatus.APPROVED,
        )
        self.gathering.current_members = 2
        self.gathering.save()

        self.client.force_authenticate(user=self.leader)
        url = f"/api/v1/gatherings/{self.gathering.id}/members/{member.id}/remove/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # DB 확인
        member.refresh_from_db()
        self.assertFalse(member.is_active)

    def test_member_status_check(self):
        """내 참여 상태 확인 테스트"""
        # 멤버 생성
        GatheringMember.objects.create(
            user=self.user1,
            gathering=self.gathering,
            status=GatheringMember.MemberStatus.PENDING,
        )

        self.client.force_authenticate(user=self.user1)
        url = f"/api/v1/gatherings/{self.gathering.id}/my-status/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["status"], "pending")
        self.assertFalse(response.data["data"]["is_leader"])
