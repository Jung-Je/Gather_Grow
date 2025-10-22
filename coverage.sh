# 커버리지 및 파이테스트 통합 도구

set -e

echo "Start pytest with coverage..."
uv run coverage run -m pytest

echo "Show coverage"
uv run coverage report --fail-under=80