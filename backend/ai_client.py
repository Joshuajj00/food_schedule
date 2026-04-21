import httpx
import json
import re
import time

from backend.logger import get_logger, TRACE

logger = get_logger('ai_client')


def _mask_headers(headers: dict) -> dict:
    masked = dict(headers)
    for key in ('Authorization', 'x-api-key'):
        if key in masked:
            v = masked[key]
            masked[key] = v[:12] + '***' if len(v) > 12 else '***'
    return masked


class AIClient:
    async def generate(self, system_prompt: str, user_prompt: str, settings) -> dict:
        fmt = settings.api_format
        provider = getattr(settings, 'provider', fmt)
        model = settings.model_name

        logger.info(f"AI 호출 시작 — provider={provider}, model={model}, format={fmt}, streaming={settings.streaming}")
        logger.debug(f"system_prompt ({len(system_prompt)}자):\n{system_prompt[:500]}")
        logger.debug(f"user_prompt ({len(user_prompt)}자):\n{user_prompt[:300]}")

        start = time.time()
        try:
            if fmt == "ollama":
                result = await self._call_ollama(system_prompt, user_prompt, settings)
            elif fmt == "openai":
                result = await self._call_openai(system_prompt, user_prompt, settings)
            elif fmt == "anthropic":
                result = await self._call_anthropic(system_prompt, user_prompt, settings)
            else:
                raise Exception(f"지원하지 않는 API 형식: {fmt}")

            elapsed = time.time() - start
            has_error = "error" in result and "breakfast" not in result and "items" not in result
            logger.info(f"AI 호출 완료 — {'오류' if has_error else '성공'}, {elapsed:.1f}초")
            logger.debug(f"파싱된 응답 ({len(str(result))}자): {str(result)[:500]}")
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"AI 호출 실패 — {elapsed:.1f}초: {e}")
            raise

    # ── Ollama ──────────────────────────────────────────────────────────────
    async def _call_ollama(self, system_prompt, user_prompt, settings) -> dict:
        url = f"{settings.base_url.rstrip('/')}/api/chat"
        final_system = self._apply_cot(system_prompt, settings)

        payload: dict = {
            "model": settings.model_name,
            "messages": [
                {"role": "system", "content": final_system},
                {"role": "user", "content": user_prompt},
            ],
            "stream": settings.streaming,
            "format": "json",
        }
        if settings.thinking_mode == "think":
            payload["think"] = True

        headers = {}
        if settings.api_key:
            headers["Authorization"] = f"Bearer {settings.api_key}"

        logger.log(TRACE, f"[Ollama] URL: {url}")
        logger.log(TRACE, f"[Ollama] 헤더: {_mask_headers(headers)}")
        logger.log(TRACE, f"[Ollama] 페이로드: {json.dumps(payload, ensure_ascii=False)}")

        async with httpx.AsyncClient(timeout=180.0) as client:
            if settings.streaming:
                return await self._collect_ollama_stream(client, url, payload, headers)
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            raw = resp.json()
            logger.log(TRACE, f"[Ollama] 원시 응답: {json.dumps(raw, ensure_ascii=False)[:2000]}")
            content = raw.get("message", {}).get("content", "{}")
            return self._parse_json(content)

    async def _collect_ollama_stream(self, client, url, payload, headers) -> dict:
        payload["stream"] = True
        text = ""
        logger.debug("[Ollama] 스트리밍 시작")
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                text += chunk.get("message", {}).get("content", "")
                if chunk.get("done"):
                    break
        logger.debug(f"[Ollama] 스트리밍 완료, 수신 {len(text)}자")
        logger.log(TRACE, f"[Ollama] 전체 수신 텍스트: {text[:2000]}")
        return self._parse_json(text)

    # ── OpenAI-compatible ────────────────────────────────────────────────────
    async def _call_openai(self, system_prompt, user_prompt, settings) -> dict:
        url = f"{settings.base_url.rstrip('/')}/v1/chat/completions"
        final_system = self._apply_cot(system_prompt, settings)

        headers = {
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        }
        if "openrouter.ai" in settings.base_url:
            headers["HTTP-Referer"] = "http://diet-assistant"
            headers["X-Title"] = "Diet Assistant"

        payload: dict = {
            "model": settings.model_name,
            "messages": [
                {"role": "system", "content": final_system},
                {"role": "user", "content": user_prompt},
            ],
            "stream": settings.streaming,
        }
        if getattr(settings, "provider", "") != "custom":
            payload["response_format"] = {"type": "json_object"}
        if settings.reasoning_effort and settings.reasoning_effort != "none":
            payload["reasoning_effort"] = settings.reasoning_effort

        logger.log(TRACE, f"[OpenAI] URL: {url}")
        logger.log(TRACE, f"[OpenAI] 헤더: {_mask_headers(headers)}")
        logger.log(TRACE, f"[OpenAI] 페이로드: {json.dumps(payload, ensure_ascii=False)}")

        async with httpx.AsyncClient(timeout=180.0) as client:
            if settings.streaming:
                return await self._collect_openai_stream(client, url, payload, headers)
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            raw = resp.json()
            logger.log(TRACE, f"[OpenAI] 원시 응답: {json.dumps(raw, ensure_ascii=False)[:2000]}")
            content = raw["choices"][0]["message"]["content"]
            return self._parse_json(content)

    async def _collect_openai_stream(self, client, url, payload, headers) -> dict:
        payload["stream"] = True
        text = ""
        logger.debug("[OpenAI] 스트리밍 시작")
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                delta = chunk["choices"][0].get("delta", {})
                text += delta.get("content") or ""
        logger.debug(f"[OpenAI] 스트리밍 완료, 수신 {len(text)}자")
        logger.log(TRACE, f"[OpenAI] 전체 수신 텍스트: {text[:2000]}")
        return self._parse_json(text)

    # ── Anthropic ────────────────────────────────────────────────────────────
    async def _call_anthropic(self, system_prompt, user_prompt, settings) -> dict:
        url = f"{settings.base_url.rstrip('/')}/v1/messages"

        headers = {
            "x-api-key": settings.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        max_tokens = 4096
        payload: dict = {
            "model": settings.model_name,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "stream": settings.streaming,
        }

        if settings.thinking_mode == "think":
            headers["anthropic-beta"] = "interleaved-thinking-2025-05-14"
            budget = settings.thinking_budget or 8000
            payload["thinking"] = {"type": "enabled", "budget_tokens": budget}
            max_tokens = budget + 4096
        elif settings.thinking_mode == "cot":
            payload["messages"][0]["content"] += "\n\n먼저 단계적으로 추론한 뒤 최종 JSON을 출력하라."

        payload["max_tokens"] = max_tokens

        logger.log(TRACE, f"[Anthropic] URL: {url}")
        logger.log(TRACE, f"[Anthropic] 헤더: {_mask_headers(headers)}")
        logger.log(TRACE, f"[Anthropic] 페이로드: {json.dumps(payload, ensure_ascii=False)}")

        async with httpx.AsyncClient(timeout=300.0) as client:
            if settings.streaming:
                return await self._collect_anthropic_stream(client, url, payload, headers)
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            raw = resp.json()
            logger.log(TRACE, f"[Anthropic] 원시 응답: {json.dumps(raw, ensure_ascii=False)[:2000]}")
            content = ""
            for block in raw.get("content", []):
                if block.get("type") == "text":
                    content = block["text"]
                    break
            return self._parse_json(content)

    async def _collect_anthropic_stream(self, client, url, payload, headers) -> dict:
        text = ""
        logger.debug("[Anthropic] 스트리밍 시작")
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if chunk.get("type") == "content_block_delta":
                    delta = chunk.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text += delta.get("text", "")
        logger.debug(f"[Anthropic] 스트리밍 완료, 수신 {len(text)}자")
        logger.log(TRACE, f"[Anthropic] 전체 수신 텍스트: {text[:2000]}")
        return self._parse_json(text)

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _apply_cot(self, system_prompt: str, settings) -> str:
        if settings.thinking_mode == "cot":
            return system_prompt + "\n\n먼저 단계적으로 추론한 뒤 최종 JSON을 출력하라."
        return system_prompt

    def _parse_json(self, text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        logger.warning(f"JSON 파싱 실패 ({len(text)}자): {text[:200]}")
        return {"error": "JSON 형식 응답을 파싱할 수 없습니다.", "raw_response": text}


ai_client = AIClient()
