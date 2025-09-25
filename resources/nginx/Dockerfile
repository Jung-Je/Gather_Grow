# Alpine 기반 Nginx 이미지 사용 (경량화)
FROM nginx:alpine

# 기본 Nginx 설정 파일 제거
RUN rm /etc/nginx/conf.d/default.conf

# 커스텀 Nginx 설정 파일 복사
COPY nginx.conf /etc/nginx/conf.d/

# HTTP 포트 80 노출
EXPOSE 80