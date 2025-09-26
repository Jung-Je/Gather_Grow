from typing import Any

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.common.responses import APIResponse
from apps.users.serializers.mypage_serializer import ProfileSerializer
from apps.users.services.services import AuthenticationService


class ProfileView(APIView):
    """사용자 프로필 관리 API
    
    인증된 사용자의 프로필 정보를 조회하고 수정합니다.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Any) -> APIResponse:
        """프로필 조회
        
        Args:
            request: HTTP 요청 객체 (인증된 사용자 필요)
        
        Returns:
            APIResponse:
                - 200: 프로필 정보 반환
                - 401: 인증 필요
        """
        user = request.user
        serializer = ProfileSerializer(user)
        return APIResponse.success(message="프로필 조회 성공", data=serializer.data)

    def patch(self, request: Any) -> APIResponse:
        """프로필 수정
        
        Args:
            request: HTTP 요청 객체
                - username (str, optional): 사용자명
                - profile (str, optional): 프로필 설명
                - profile_image (file, optional): 프로필 이미지
                - education_level (str, optional): 학력
                - location (str, optional): 지역
        
        Returns:
            APIResponse:
                - 200: 프로필 수정 성공
                - 400: 잘못된 입력 데이터
                - 401: 인증 필요
        """
        try:
            user = request.user
            serializer = ProfileSerializer(user, data=request.data, partial=True, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return APIResponse.success(message="프로필 수정 성공", data=serializer.data)
        except Exception as e:
            return APIResponse.from_exception(e, message="프로필 수정에 실패했습니다.", log_error=False)


class PasswordChangeView(APIView):
    """비밀번호 변경 API
    
    인증된 사용자의 비밀번호를 변경합니다.
    현재 비밀번호 확인 후 새 비밀번호로 변경합니다.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request: Any) -> APIResponse:
        """비밀번호 변경 처리
        
        마이페이지에서 현재 비밀번호 확인 후 새 비밀번호로 변경.
        로그인한 상태에서만 사용 가능합니다.
        
        Args:
            request: HTTP 요청 객체
                - old_password (str): 현재 비밀번호
                - new_password (str): 새 비밀번호
        
        Returns:
            APIResponse:
                - 200: 비밀번호 변경 성공
                - 400: 현재 비밀번호 불일치 또는 잘못된 입력
                - 401: 인증 필요
        """
        try:
            user = request.user
            old_password = request.data.get("old_password")
            new_password = request.data.get("new_password")
            
            if not old_password or not new_password:
                return APIResponse.bad_request(message="현재 비밀번호와 새 비밀번호를 모두 입력해주세요.")
            
            AuthenticationService.change_password(user, old_password, new_password)
            return APIResponse.success(message="비밀번호가 성공적으로 변경되었습니다.")
            
        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(e, message="비밀번호 변경에 실패했습니다.", log_error=False)
