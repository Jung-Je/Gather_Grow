from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.chat.serializers.message_serializer import (
    ChatMessageCreateSerializer,
    ChatMessageListSerializer,
)
from apps.chat.services.message_service import ChatMessageService
from apps.common.responses import APIResponse
from apps.gatherings.services.member_service import MemberService


class ChatMessagePagination(PageNumberPagination):
    """채팅 메시지 페이지네이션"""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class ChatMessageListView(APIView):
    """채팅 메시지 목록 조회 및 생성 API"""

    permission_classes = [IsAuthenticated]

    def get(self, request, gathering_id: int):
        """채팅 메시지 목록 조회

        Args:
            gathering_id: 모임 ID
            request: HTTP 요청 객체

        Query Parameters:
            page (int): 페이지 번호 (default: 1)
            page_size (int): 페이지 크기 (default: 50, max: 100)

        Returns:
            APIResponse:
                - 200: 채팅 메시지 목록 (페이지네이션)
                - 403: 권한 없음 (모임 멤버가 아님)
                - 404: 존재하지 않는 모임
        """
        try:
            # 권한 확인: 승인된 모임 멤버만 조회 가능
            ChatMessageService.check_member_permission(gathering_id=gathering_id, user=request.user)

            # 메시지 목록 조회
            messages = ChatMessageService.get_messages(gathering_id=gathering_id)

            # 페이지네이션
            paginator = ChatMessagePagination()
            paginated_messages = paginator.paginate_queryset(messages, request)

            serializer = ChatMessageListSerializer(paginated_messages, many=True)
            return paginator.get_paginated_response(serializer.data)

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except PermissionError as e:
            return APIResponse.forbidden(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(e, message="채팅 메시지 조회에 실패했습니다.")

    def post(self, request, gathering_id: int):
        """채팅 메시지 전송

        Args:
            gathering_id: 모임 ID
            request: HTTP 요청 객체
                - message (str): 메시지 내용 (선택)
                - image (file): 이미지 파일 (선택)

        Returns:
            APIResponse:
                - 201: 메시지 전송 성공
                - 400: 잘못된 입력 (텍스트/이미지 중 하나는 필수)
                - 403: 권한 없음 (모임 멤버가 아님)
                - 404: 존재하지 않는 모임
        """
        try:
            # 권한 확인: 승인된 모임 멤버만 메시지 전송 가능
            ChatMessageService.check_member_permission(gathering_id=gathering_id, user=request.user)

            # 데이터 검증
            serializer = ChatMessageCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # 메시지 생성
            message = ChatMessageService.create_message(
                gathering_id=gathering_id,
                user=request.user,
                message_text=serializer.validated_data.get("message"),
                image=serializer.validated_data.get("image"),
            )

            result_serializer = ChatMessageListSerializer(message)
            return APIResponse.created(message="메시지를 전송했습니다.", data=result_serializer.data)

        except ValueError as e:
            return APIResponse.bad_request(message=str(e))
        except PermissionError as e:
            return APIResponse.forbidden(message=str(e))
        except Exception as e:
            return APIResponse.from_exception(e, message="메시지 전송에 실패했습니다.")
