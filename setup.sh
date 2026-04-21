#!/bin/bash
set -e
docker compose up -d
IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
echo "접속 주소: http://${IP}:8000"
echo "설정 탭에서 사용할 API 제공자와 키를 입력하세요."
