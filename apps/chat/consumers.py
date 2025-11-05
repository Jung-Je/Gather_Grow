import json
import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils.html import escape
from rest_framework_simplejwt.tokens import AccessToken

from apps.chat.models import ChatMessage
from apps.chat.serializers.message_serializer import ChatMessageListSerializer
from apps.gatherings.models import Gathering, GatheringMember
from apps.users.models import User

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """채팅 WebSocket Consumer

    실시간 채팅 메시지 전송 및 수신을 처리합니다.
    """

    async def connect(self):
        """WebSocket 연결 처리

        사용자 인증 및 채팅방 멤버십을 확인한 후
        연결을 수락하고 그룹에 추가합니다.
        """
        try:
            self.gathering_id = self.scope["url_route"]["kwargs"]["gathering_id"]
            self.room_group_name = f"chat_{self.gathering_id}"

            logger.info(f"WebSocket connection attempt to gathering {self.gathering_id}")

            # JWT 토큰으로 사용자 인증
            self.user = await self.get_user_from_token()

            logger.info(
                "WebSocket connection attempt",
                extra={
                    "gathering_id": self.gathering_id,
                    "user_id": getattr(self.user, "id", None),
                    "is_authenticated": self.user is not None,
                },
            )

            # 인증 확인
            if not self.user:
                logger.warning(
                    "Unauthenticated user connection rejected",
                    extra={"gathering_id": self.gathering_id},
                )
                await self.close()
                return

            # 권한 확인: 승인된 멤버만 입장 가능
            has_permission = await self.check_member_permission()
            if not has_permission:
                logger.warning(
                    "Non-member connection rejected",
                    extra={"gathering_id": self.gathering_id, "user_id": self.user.id},
                )
                await self.close()
                return

            # 채팅방 그룹에 추가
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            logger.info(
                "WebSocket connection successful",
                extra={"gathering_id": self.gathering_id, "user_id": self.user.id},
            )
        except Exception as e:
            logger.error(f"WebSocket connect error: {str(e)}", exc_info=True)
            await self.close()

    async def disconnect(self, close_code):
        """WebSocket 연결 해제"""
        # 채팅방 그룹에서 제거
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        logger.info(
            f"WebSocket disconnected: user_id={self.user.id}, gathering_id={self.gathering_id}, code={close_code}"
        )

    async def receive(self, text_data):
        """클라이언트로부터 메시지 수신"""
        try:
            data = json.loads(text_data)
            message_text = data.get("message")
            # image는 WebSocket으로 전송하지 않고 HTTP API 사용

            # 메시지 저장
            message = await self.save_message(message_text)

            # 메시지 직렬화
            serializer_data = await self.serialize_message(message)

            # 채팅방 그룹의 모든 사용자에게 브로드캐스트
            await self.channel_layer.group_send(
                self.room_group_name, {"type": "chat_message", "message": serializer_data}
            )

        except Exception as e:
            logger.error(
                f"Error receiving message: user_id={self.user.id}, gathering_id={self.gathering_id}, error={str(e)}"
            )
            await self.send(text_data=json.dumps({"error": "메시지 전송에 실패했습니다."}))

    async def chat_message(self, event):
        """채팅방 그룹으로부터 메시지를 받아 클라이언트에 전송"""
        message = event["message"]

        await self.send(text_data=json.dumps({"message": message}))

    @database_sync_to_async
    def check_member_permission(self) -> bool:
        """모임 멤버 권한 확인"""
        try:
            gathering = Gathering.objects.get(id=self.gathering_id)
        except Gathering.DoesNotExist:
            return False

        # 모임장은 무조건 허용
        if gathering.user == self.user:
            return True

        # 승인된 멤버인지 확인
        return GatheringMember.objects.filter(
            gathering=gathering,
            user=self.user,
            status=GatheringMember.MemberStatus.APPROVED,
            is_active=True,
        ).exists()

    @database_sync_to_async
    def save_message(self, message_text: str):
        """메시지 DB 저장"""
        try:
            gathering = Gathering.objects.get(id=self.gathering_id)
        except Gathering.DoesNotExist:
            raise ValueError("존재하지 않는 모임입니다.")

        if not message_text:
            raise ValueError("메시지 내용을 입력해주세요.")

        message = ChatMessage.objects.create(gathering=gathering, user=self.user, message=message_text)

        logger.info(
            f"Chat message created via WebSocket: message_id={message.id}, gathering_id={self.gathering_id}, user_id={self.user.id}"
        )

        return message

    @database_sync_to_async
    def serialize_message(self, message):
        """메시지 직렬화"""
        serializer = ChatMessageListSerializer(message)
        return serializer.data

    @database_sync_to_async
    def get_user_from_token(self):
        """JWT 토큰에서 사용자 인증"""
        try:
            # 쿼리 파라미터에서 토큰 추출
            query_string = self.scope.get("query_string", b"").decode()
            logger.debug(f"WebSocket query string: {query_string}")
            query_params = parse_qs(query_string)
            token = query_params.get("token", [None])[0]

            if not token:
                logger.warning("No token provided in WebSocket connection")
                return None

            logger.debug(f"Token received: {token[:20]}...")

            # JWT 토큰 검증
            access_token = AccessToken(token)
            user_id = access_token["user_id"]
            logger.debug(f"Token validated for user_id: {user_id}")

            # 사용자 조회
            user = User.objects.get(id=user_id)
            logger.info(f"User authenticated via WebSocket: {user.username} (id={user.id})")
            return user

        except Exception as e:
            logger.error(f"Error authenticating WebSocket user: {str(e)}", exc_info=True)
            return None
