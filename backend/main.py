from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from backend.database import init_db
import backend.logger  # noqa: F401 — 로깅 초기화
from backend.routers import ingredients, meal, budget
from backend.routers import settings as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title='혈당 관리 식단 어시스턴트',
    description='보유 식재료를 기반으로 혈당 관리를 위한 식단을 추천합니다.',
    version='1.0.0',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(ingredients.router)
app.include_router(meal.router)
app.include_router(budget.router)
app.include_router(settings_router.router)

frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
if os.path.exists(os.path.join(frontend_path, 'index.html')):
    app.mount('/static', StaticFiles(directory=frontend_path), name='static')

@app.get('/', include_in_schema=False)
async def root():
    frontend_file = os.path.join(frontend_path, 'index.html')
    if os.path.exists(frontend_file):
        return FileResponse(frontend_file)
    return {'message': '혈당 관리 식단 어시스턴트 API 서버'}

@app.get('/health')
async def health_check():
    return {'status': 'healthy', 'message': '서버가 정상적으로 실행 중입니다.'}