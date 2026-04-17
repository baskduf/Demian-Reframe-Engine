from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
TERMINAL_STATES = {"close_session", "crisis", "out_of_scope"}


def post_json(base_url: str, path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(base_url: str, path: str) -> dict:
    with urllib.request.urlopen(f"{base_url}{path}") as response:
        return json.loads(response.read().decode("utf-8"))


def prompt(text: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value if value else default


def prompt_bool(text: str, default: bool = False) -> bool:
    default_text = "y" if default else "n"
    while True:
        value = prompt(text, default_text).lower()
        if value in {"y", "yes", "true", "1"}:
            return True
        if value in {"n", "no", "false", "0"}:
            return False
        print("y 또는 n으로 입력해주세요.")


def prompt_int(text: str, default: int) -> int:
    while True:
        value = prompt(text, str(default))
        try:
            return int(value)
        except ValueError:
            print("숫자로 입력해주세요.")


def prompt_list(text: str) -> list[str]:
    value = prompt(text)
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def print_response(response: dict) -> None:
    template = response.get("template_response") or {}
    guidance = response.get("guidance") or {}
    clarification = response.get("clarification") or {}
    choices = response.get("choices") or {}
    collected_slots = response.get("collected_slots") or {}
    state_data = response.get("state_data") or {}

    print("-" * 30)
    print("current_state      =", response.get("current_state"))
    print("interaction_status =", response.get("interaction_status"))
    print("template_id        =", template.get("template_id"))
    print("message            =", template.get("message"))

    if guidance:
        print()
        print(f"[{guidance.get('title')}]")
        print(guidance.get("description"))
        for example in guidance.get("examples", []):
            print("예시:", example)

    if clarification:
        print()
        print("[재질문]")
        print("사유:", clarification.get("reason_code"))
        print("안내:", clarification.get("message"))
        if clarification.get("missing_fields"):
            print("보완 필요:", ", ".join(clarification["missing_fields"]))
        for example in clarification.get("examples", []):
            print("예시:", example)

    if choices:
        print()
        print("[선택지]")
        for group_name, options in choices.items():
            print(f"- {group_name}")
            for index, option in enumerate(options, start=1):
                print(f"  {index}. {option.get('option_id')} / {option.get('label')} / {option.get('description')}")

    if collected_slots:
        print()
        print("[현재까지 수집된 값]")
        for key, value in collected_slots.items():
            print(f"- {key}: {value}")

    if state_data.get("final_summary"):
        print()
        print("[최종 요약]")
        print(state_data["final_summary"])

    print()


def choice_input(group: list[dict], text: str) -> str:
    raw = prompt(text)
    if raw.isdigit():
        index = int(raw) - 1
        if 0 <= index < len(group):
            return str(group[index]["option_id"])
    return raw


def build_payload_for_state(state: str, response: dict) -> tuple[str, dict] | None:
    choices = response.get("choices") or {}

    if state == "eligibility_check":
        return "eligibility", {
            "is_adult": prompt_bool("성인인가요? (y/n)"),
            "target_condition": prompt("목표 상태를 입력하세요", "gad"),
        }

    if state == "situation_capture":
        return "situation", {
            "situation_text": prompt("어떤 상황이 있었나요"),
            "trigger_text": prompt("무엇이 걱정을 촉발했나요"),
        }

    if state == "worry_thought_capture":
        return "worry", {
            "automatic_thought": prompt("그 순간 스친 자동적 사고는 무엇인가요"),
            "worry_prediction": prompt("최악의 예측은 무엇인가요"),
        }

    if state == "emotion_body_behavior_capture":
        emotion_choices = choices.get("emotion_labels", [])
        emotion_label = choice_input(emotion_choices, "대표 감정 라벨 번호 또는 값을 입력하세요") if emotion_choices else prompt("대표 감정 라벨")
        return "emotion", {
            "emotions": [{"label": emotion_label, "intensity": prompt_int("감정 강도는 몇 점인가요 (0-100)", 80)}],
            "body_symptoms": prompt_list("몸 반응을 쉼표로 구분해 입력하세요"),
            "safety_behaviors": prompt_list("안전행동을 쉼표로 구분해 입력하세요"),
        }

    if state == "distortion_hypothesis":
        distortion_choices = choices.get("distortion_candidates", [])
        selected = choice_input(distortion_choices, "왜곡 후보 번호 또는 ID를 입력하세요 (비우면 기본 후보 사용)")
        selected_values = [selected] if selected else []
        return "distortion", {"selected_distortion_ids": selected_values}

    if state == "evidence_for":
        return "evidence_for", {"evidence_for": prompt_list("걱정을 지지하는 근거를 쉼표로 입력하세요")}

    if state == "evidence_against":
        return "evidence_against", {"evidence_against": prompt_list("반대 근거나 예외를 쉼표로 입력하세요")}

    if state == "alternative_thought":
        return "alternative", {
            "balanced_view": prompt("균형 잡힌 관점을 적어주세요"),
            "coping_statement": prompt("실행할 대응 문장을 적어주세요"),
        }

    if state == "re_rate_anxiety":
        return "rerate", {
            "re_rated_anxiety": prompt_int("지금 불안 점수는 몇 점인가요 (0-100)", 50),
            "experiment_required": prompt_bool("행동실험이 필요한가요? (y/n)"),
        }

    if state == "behavior_experiment":
        return "experiment", {
            "action": prompt("행동실험 액션을 적어주세요"),
            "timebox": prompt("언제까지/얼마나 할지 적어주세요"),
            "hypothesis": prompt("검증하고 싶은 가설이 있으면 적어주세요 (선택)"),
        }

    if state == "summary_plan":
        return "summary", {"summary_ack": prompt_bool("요약을 확인하고 종료할까요? (y/n)", True)}

    return None


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL
    print("=" * 50)
    print("Demian Reframe Engine - Interactive CMD Demo")
    print("Base URL:", base_url)
    print("다른 창에서 API 서버를 먼저 실행하세요:")
    print("  python -m uvicorn app.main:app --reload")
    print("=" * 50)
    print()

    try:
        create = post_json(base_url, "/v1/sessions", {"user_id": "cmd-demo-user", "locale": "ko-KR"})
        session_id = create["session"]["session_id"]
        print("session_id =", session_id)
        print_response(create)

        risk_payload = {
            "free_text": prompt("위험 스크린 자유입력 (비워도 됨)"),
            "suicidal_intent": prompt_bool("자살 의도가 있나요? (y/n)", False),
            "suicidal_plan": prompt_bool("구체적 계획이 있나요? (y/n)", False),
            "means_access": prompt_bool("수단 접근 가능성이 있나요? (y/n)", False),
            "command_hallucination": prompt_bool("명령형 환청이 있나요? (y/n)", False),
            "psychotic_language": prompt_bool("현실검증 저하/정신병적 표현이 있나요? (y/n)", False),
            "acute_deterioration": prompt_bool("급격한 악화가 있나요? (y/n)", False),
        }
        response = post_json(base_url, f"/v1/sessions/{session_id}/risk-screen", risk_payload)
        print_response(response)

        while response.get("current_state") not in TERMINAL_STATES:
            built = build_payload_for_state(str(response["current_state"]), response)
            if built is None:
                print("이 상태에 대한 입력 핸들러가 없습니다.")
                break
            event_type, payload = built
            if event_type == "experiment" and not payload.get("hypothesis"):
                payload.pop("hypothesis", None)
            response = post_json(
                base_url,
                f"/v1/sessions/{session_id}/events",
                {"event_type": event_type, "payload": payload},
            )
            print_response(response)

        artifacts = get_json(base_url, f"/v1/sessions/{session_id}/artifacts")
        thought_record = artifacts["thought_record"]
        print("-" * 30)
        print("최종 아티팩트")
        print("selected_distortion_ids =", thought_record.get("selected_distortion_ids"))
        print("alternative_thought     =", thought_record.get("alternative_thought"))
        print("re_rated_anxiety        =", thought_record.get("re_rated_anxiety"))
        print("final_summary           =", thought_record.get("final_summary"))
        print()
        return 0
    except urllib.error.HTTPError as exc:
        print("[HTTP ERROR]", exc.code, exc.reason)
        print(exc.read().decode("utf-8", errors="replace"))
        return 1
    except urllib.error.URLError as exc:
        print("[CONNECTION ERROR]", exc.reason)
        print("API 서버가 실행 중인지 확인해주세요.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
