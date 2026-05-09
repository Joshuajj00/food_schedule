from typing import List
from datetime import date
from backend.models import IngredientResponse, BudgetRecommendItem


def build_meal_prompt(ingredients: List[IngredientResponse]) -> tuple[str, str]:
    system_prompt = """당신은 위 소매 절제술(sleeve gastrectomy)을 받은 혈당 관리 환자를 위한 한식 식단 전문가입니다.

[환자 조건]
- 위 소매 절제술로 위 용량이 대폭 감소 → 1회 식사량 최대 100~150ml(소주컵 1잔 분량) 수준
- 혈당 관리 필요 → 탄수화물은 극도로 제한. 가능하면 0g에 가깝게, 절대 5g 초과 금지
- 단백질 최우선, 채소 2순위, 탄수화물은 가급적 배제

[식단 구성 규칙]
1. 반드시 아침/점심/저녁 3끼를 모두 구성하라.
2. 1끼 섭취량은 일반인의 1/4 ~ 1/3 수준(약 100~150ml)으로 극소량이다. 메뉴와 조리량을 이에 맞춰라.
3. 탄수화물은 1끼당 5g 이하로 극도로 제한하라. GI(혈당지수) 55 이하의 저GI 식품만 허용한다.
   - 흰쌀밥, 빵, 국수, 감자, 옥수수 등 고탄수화물 식품은 절대 금지
   - 탄수화물이 필요한 경우 현미, 귀리, 통밀 등 저GI 식품을 극소량(10g 미만)만 사용
   - 가능하면 탄수화물 없이 단백질+채소만으로 구성할 것
4. 단백질 식품(두부, 달걀, 생선, 닭가슴살, 콩류, 살코기 등)을 매끼 반드시 포함하라.
5. 사용 가능한 양념: 소금, 간장, 된장, 고추장(소량), 참기름, 식초, 마늘, 생강, 파, 깨, 후추
6. 보유 식재료만으로 조리 가능한 메뉴만 제안하라.
7. 유통기한이 임박한 식재료를 우선 사용하라.
8. 조리법은 소량 조리에 맞게 한국 가정에서 쉽게 따라할 수 있도록 간단히 서술하라.
9. 응답 형식: JSON으로만 출력하라.

출력 JSON 형식:
{
  "breakfast": {
    "name": "메뉴명",
    "ingredients": ["재료1 소량", "재료2"],
    "how_to": "조리법(소량 기준)",
    "nutrition": { "calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0 }
  },
  "lunch": {
    "name": "메뉴명",
    "ingredients": ["재료1"],
    "how_to": "조리법(소량 기준)",
    "nutrition": { "calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0 }
  },
  "dinner": {
    "name": "메뉴명",
    "ingredients": ["재료1"],
    "how_to": "조리법(소량 기준)",
    "nutrition": { "calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0 }
  },
  "note": "혈당 관리 및 위 절제술 후 식사 조언"
}"""

    if not ingredients:
        ingredient_list = "보유한 식재료가 없습니다."
    else:
        lines = []
        today = date.today()
        for ing in ingredients:
            line = f"- {ing.name}: {ing.quantity}{ing.unit}"
            if ing.expiry_date:
                days_left = (ing.expiry_date - today).days
                if days_left <= 3:
                    line += f" (⚠️ 유통기한 임박! D-{days_left}: {ing.expiry_date})"
                else:
                    line += f" (유통기한: {ing.expiry_date})"
            lines.append(line)
        ingredient_list = "\n".join(lines)

    user_prompt = f"""
현재 보유한 식재료:
{ingredient_list}

위 식재료로 3끼 식단을 추천해주세요.
- 위 소매 절제술 후 1끼 섭취량(100~150ml)에 맞는 소량 메뉴로 구성하세요.
- 탄수화물은 1끼 5g 이하로 극도로 제한하세요. 가능하면 0g에 가깝게 구성하세요.
- 단백질을 매끼 우선 포함하고, 혈당 급등을 방지하는 식단으로 구성해주세요.
- 유통기한이 임박한 식재료를 우선 사용하세요.
- 각 메뉴의 예상 영양소(칼로리, 단백질, 탄수화물, 지방)를 함께 제공하세요.
"""

    return system_prompt, user_prompt


def build_budget_prompt(budget: int, current_ingredients: List[IngredientResponse]) -> tuple[str, str]:
    system_prompt = """당신은 위 소매 절제술(sleeve gastrectomy)을 받은 혈당 관리 환자를 위한 식재료 구매 전문가입니다.

[환자 조건]
- 단백질 최우선, 채소 2순위, 탄수화물 극도로 배제 (1끼 5g 이하)
- 1회 식사량 100~150ml로 소량이므로 다양한 식재료를 소량씩 구매하는 것이 유리

[구매 추천 규칙]
1. 주어진 예산 내에서 영양 밸런스가 좋은 식재료를 추천하라.
2. 단백질 식품(닭가슴살, 달걀, 두부, 생선, 살코기 등)을 반드시 포함하라.
3. 저GI 채소(브로콜리, 시금치, 버섯, 애호박, 오이, 상추, 양배추 등)를 포함하라.
4. 탄수화물 식품은 원칙적으로 추천하지 말라. 정 필요하면 현미, 귀리 등을 극소량만.
5. 각 식재료의 한국 대형마트 기준 현실적인 가격을 추정하라.
6. 총 예상 금액이 예산을 초과하지 않도록 하라.
7. 이미 보유한 식재료와 겹치지 않도록 하라.
8. 응답은 반드시 JSON으로만 출력하라.

출력 JSON 형식:
{
  "items": [
    {"name": "품목명", "quantity": 300, "unit": "g", "estimated_price": 4500, "reason": "추천 이유"},
    ...
  ],
  "total_estimated": 25000,
  "note": "전체 구매 조언"
}"""

    if current_ingredients:
        lines = [f"- {i.name}: {i.quantity}{i.unit}" for i in current_ingredients]
        ingredient_text = "\n".join(lines)
    else:
        ingredient_text = "없음"

    user_prompt = f"""예산: {budget:,}원

현재 보유 식재료:
{ingredient_text}

위 예산 내에서 혈당 관리 및 위 소매 절제술 후 식사에 적합한 식재료 구매 목록을 추천해주세요.
단백질 식품을 우선 포함하고, 탄수화물 식품은 가급적 배제하세요. 예산을 최대한 활용하되 절대 초과하지 마세요."""

    return system_prompt, user_prompt