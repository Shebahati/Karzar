# Local Stack Access

## Typical local URLs

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/api/docs |
| Storefront | http://localhost:3000 |
| Admin Panel | http://localhost:3001 |

Frontends should set `NEXT_PUBLIC_USE_MOCK=false` and `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1` in `.env.local` (not committed).

## Credentials

Use values from your local `backend/.env` bootstrap (admin phone/password, step-up PIN, `OTP_DEV_ECHO`). Do not commit real secrets here.

## Notes

- Prefer `docker compose … start` when containers already exist.
- Storefront OTP: when echo is enabled, read `dev_code` from the OTP request response.
