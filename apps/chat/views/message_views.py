from drf_spectacular.utils import OpenApiParameter, extend_schema
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

    @extend_schema(
        summary="채팅 메시지 목록 조회",
        description="모임의 채팅 메시지 목록을 조회합니다. 승인된 모임 멤버만 조회 가능합니다.",
        parameters=[
            OpenApiParameter(
                name="gathering_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="모임 ID",
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="페이지 번호 (기본값: 1)",
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                description="페이지 크기 (기본값: 50, 최대: 100)",
            ),
        ],
        responses={
            200: ChatMessageListSerializer(many=True),
            403: {"description": "권한 없음 (모임 멤버가 아님)"},
            404: {"description": "존재하지 않는 모임"},
        },
        tags=["채팅"],
    )
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

    @extend_schema(
        summary="채팅 메시지 전송",
        description="모임에 채팅 메시지를 전송합니다. 텍스트 또는 이미지 중 최소 하나는 필수입니다. 승인된 모임 멤버만 전송 가능합니다.",
        parameters=[
            OpenApiParameter(
                name="gathering_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="모임 ID",
            ),
        ],
        request=ChatMessageCreateSerializer,
        responses={
            201: ChatMessageListSerializer,
            400: {"description": "잘못된 입력 (텍스트/이미지 중 하나는 필수)"},
            403: {"description": "권한 없음 (모임 멤버가 아님)"},
            404: {"description": "존재하지 않는 모임"},
        },
        tags=["채팅"],
    )
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
