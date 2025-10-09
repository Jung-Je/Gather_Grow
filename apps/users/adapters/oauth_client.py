"""OAuth2 Client Wrapper

dj-rest-auth와의 호환성을 위한 OAuth2Client 래퍼
"""

from allauth.socialaccount.providers.oauth2.client import OAuth2Client


class CustomOAuth2Client(OAuth2Client):
    """커스텀 OAuth2 클라이언트

    dj-rest-auth가 scope_delimiter를 중복으로 전달하는 문제를 해결합니다.
    """

    def __init__(
        self,
        request,
        consumer_key,
        consumer_secret,
        access_token_method="POST",
        access_token_url=None,
        callback_url=None,
        scope=None,  # scope는 받지만 사용하지 않음
        scope_delimiter=" ",
        headers=None,
        basic_auth=False,
        **kwargs,
    ):
        """OAuth2Client 초기화

        scope 파라미터는 무시하고 나머지를 부모 클래스에 전달합니다.
        """
        # OAuth2Client는 scope를 받지 않으므로 제거
        super().__init__(
            request=request,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token_method=access_token_method,
            access_token_url=access_token_url,
            callback_url=callback_url,
            scope_delimiter=scope_delimiter,
            headers=headers,
            basic_auth=basic_auth,
        )
