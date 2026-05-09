import sqlite3
from pathlib import Path
from datetime import date, timedelta

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / 'data' / 'test_diet.db'

if DB_PATH.exists():
    DB_PATH.unlink()

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute('''
CREATE TABLE ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL,
    category TEXT DEFAULT '기타',
    expiry_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

# 프로젝트 조건에 부합하는 식재료 30개
today = date.today()
items = [
    ('닭가슴살', 500, 'g', '단백질', today + timedelta(days=5)),
    ('두부', 400, 'g', '단백질', today + timedelta(days=3)),
    ('계란', 12, '개', '단백질', today + timedelta(days=10)),
    ('연어', 300, 'g', '단백질', today + timedelta(days=4)),
    ('참치캔', 2, '개', '단백질', today + timedelta(days=180)),
    ('그릭 요거트', 500, 'g', '유제품', today + timedelta(days=7)),
    ('코티지 치즈', 250, 'g', '유제품', today + timedelta(days=8)),
    ('버섯', 300, 'g', '채소', today + timedelta(days=5)),
    ('시금치', 200, 'g', '채소', today + timedelta(days=3)),
    ('브로콜리', 250, 'g', '채소', today + timedelta(days=4)),
    ('애호박', 300, 'g', '채소', today + timedelta(days=3)),
    ('양배추', 400, 'g', '채소', today + timedelta(days=7)),
    ('아보카도', 2, '개', '채소', today + timedelta(days=5)),
    ('방울토마토', 200, 'g', '채소', today + timedelta(days=4)),
    ('피망', 200, 'g', '채소', today + timedelta(days=6)),
    ('청경채', 200, 'g', '채소', today + timedelta(days=4)),
    ('마늘', 100, 'g', '양념', today + timedelta(days=30)),
    ('생강', 100, 'g', '양념', today + timedelta(days=14)),
    ('간장', 500, 'ml', '양념', today + timedelta(days=365)),
    ('된장', 300, 'g', '양념', today + timedelta(days=180)),
    ('참기름', 200, 'ml', '양념', today + timedelta(days=365)),
    ('올리브유', 250, 'ml', '양념', today + timedelta(days=365)),
    ('아몬드', 200, 'g', '단백질', today + timedelta(days=90)),
    ('치아씨드', 150, 'g', '기타', today + timedelta(days=180)),
    ('호두', 150, 'g', '단백질', today + timedelta(days=90)),
    ('새우', 300, 'g', '단백질', today + timedelta(days=4)),
    ('닭안심', 400, 'g', '단백질', today + timedelta(days=4)),
    ('양파', 300, 'g', '채소', today + timedelta(days=7)),
    ('파프리카', 200, 'g', '채소', today + timedelta(days=5)),
    ('청양고추', 50, 'g', '채소', today + timedelta(days=10)),
    ('미역', 50, 'g', '기타', today + timedelta(days=365)),
]

# 프로젝트 조건에 부합하지 않는 식재료 10개
items += [
    ('백미', 1000, 'g', '탄수화물', today + timedelta(days=60)),
    ('식빵', 1, '봉지', '탄수화물', today + timedelta(days=7)),
    ('라면', 5, '개', '탄수화물', today + timedelta(days=180)),
    ('감자', 1000, 'g', '탄수화물', today + timedelta(days=20)),
    ('옥수수통조림', 3, '개', '탄수화물', today + timedelta(days=90)),
    ('바나나', 6, '개', '탄수화물', today + timedelta(days=4)),
    ('사과', 4, '개', '탄수화물', today + timedelta(days=10)),
    ('시리얼', 500, 'g', '탄수화물', today + timedelta(days=120)),
    ('꿀', 300, 'g', '기타', today + timedelta(days=180)),
    ('초콜릿', 100, 'g', '기타', today + timedelta(days=150)),
]

cur.executemany(
    'INSERT INTO ingredients (name, quantity, unit, category, expiry_date) VALUES (?, ?, ?, ?, ?)',
    [(name, quantity, unit, category, expiry.isoformat() if expiry else None) for name, quantity, unit, category, expiry in items]
)

conn.commit()
conn.close()

print(f'Created {DB_PATH} with {len(items)} ingredients.')
