# 로컬 TagScope 외부 공유 가이드

이 문서는 내 컴퓨터에서 실행 중인 TagScope를 외부 사람이 볼 수 있게 여는 방법입니다.

구조는 아래처럼 봅니다.

```text
외부 사용자
  |
  v
Cloudflare Tunnel 공개 URL
  |
  v
Caddy
  |
  ├── /api/* -> TagScope backend
  └── /*     -> TagScope frontend
```

즉, 외부에는 주소 하나만 공유하고 내부에서 Caddy가 화면 요청과 API 요청을 나눠 보냅니다.

## 1. 준비물

- Docker Desktop
- 현재 프로젝트의 `.env`
- `data/insta_pipeline.duckdb`
- TagScope backend / frontend가 빌드될 수 있는 상태

주의:

- Airflow `8082`는 외부에 공개하지 않습니다.
- `.env`, `secrets/storage_state.json`, `data/insta_pipeline.duckdb`는 공유하지 않습니다.
- 내 컴퓨터가 꺼지거나 잠자기 모드에 들어가면 외부 접속도 끊깁니다.

## 2. 빠른 공유 URL로 열기

Cloudflare 계정 설정 없이 임시 URL을 받는 방식입니다.

```bash
docker compose -f docker-compose.yaml -f docker-compose.share.yaml --profile quick-share up -d --build caddy cloudflared-quick
```

공개 URL 확인:

```bash
docker compose -f docker-compose.yaml -f docker-compose.share.yaml logs -f cloudflared-quick
```

로그에서 아래처럼 생긴 URL을 찾습니다.

```text
https://something.trycloudflare.com
```

이 주소를 외부 사람에게 공유하면 됩니다.

로컬에서 Caddy 경유 접속을 먼저 확인하려면 아래 주소를 엽니다.

```text
http://localhost:8088/taggers
http://localhost:8088/co-brands
http://localhost:8088/health
```

## 3. 고정 도메인으로 열기

Cloudflare에서 Named Tunnel을 만든 뒤 토큰을 `.env`에 넣습니다.

```env
CLOUDFLARE_TUNNEL_TOKEN=<cloudflare_tunnel_token>
```

실행:

```bash
docker compose -f docker-compose.yaml -f docker-compose.share.yaml --profile share up -d --build caddy cloudflared
```

토큰을 별도 파일 `.env.share`에 넣고 싶다면 아래처럼 실행합니다.

```bash
docker compose --env-file .env.share -f docker-compose.yaml -f docker-compose.share.yaml --profile share up -d --build caddy cloudflared
```

상태 확인:

```bash
docker compose -f docker-compose.yaml -f docker-compose.share.yaml ps
docker compose -f docker-compose.yaml -f docker-compose.share.yaml logs -f cloudflared
```

## 4. 종료

임시 공유 종료:

```bash
docker compose -f docker-compose.yaml -f docker-compose.share.yaml --profile quick-share down
```

고정 터널 종료:

```bash
docker compose -f docker-compose.yaml -f docker-compose.share.yaml --profile share down
```

## 5. 자주 헷갈리는 점

`localhost:3000`을 그대로 공유할 수는 없습니다.

`localhost`는 내 컴퓨터 안에서만 통하는 주소입니다. Cloudflare Tunnel이 외부 주소를 만들고, Caddy가 그 요청을 `tagscope-frontend`와 `tagscope-backend`로 나눠 보내야 외부에서도 화면과 API가 함께 동작합니다.

프론트엔드는 공유 모드에서 API를 같은 주소의 `/api`로 호출합니다.

```text
https://something.trycloudflare.com/api/brands
```

그래서 외부 사용자 브라우저가 `localhost:8000`을 찾는 문제가 생기지 않습니다.
