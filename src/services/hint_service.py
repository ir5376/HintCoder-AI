class HintService:

    def get_hint(self, problem: dict, student_code: str, hint_level: int) -> str:
        if hint_level <= 1:
            return (
                "힌트 1: 문제를 먼저 천천히 읽고, 입력과 출력 요구사항을 확인하세요."
            )
        if hint_level == 2:
            return (
                "힌트 2: 문제를 작은 단계로 나누고, 주요 연산을 어떻게 구현할지 생각하세요."
            )
        if hint_level >= 3:
            return (
                "힌트 3: 코드 흐름을 따라가며 변수와 반복문의 역할을 점검하고 수정하세요."
            )
        return "힌트 레벨은 1에서 3 사이로 설정해 주세요."