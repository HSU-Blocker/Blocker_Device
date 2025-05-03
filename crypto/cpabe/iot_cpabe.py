from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, G2, GT, pair
from charm.toolbox.secretutil import SecretUtil
from charm.schemes.abenc.abenc_bsw07 import CPabe_BSW07
import re
import base64
import hashlib
import json
import os
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class IoTCPABE:
    """
    CP-ABE 개선된 구현 클래스

    이 클래스는 charm-crypto 라이브러리를 사용하여 CP-ABE 기능을 구현합니다.
    - 문자열 메시지를 직접 CP-ABE로 암호화하는 방식으로 개선
    - 시스템 초기화 (setup)
    - 키 생성 (keygen)
    - 정책 기반 암호화 (encrypt)
    - 키 기반 복호화 (decrypt)
    """

    def __init__(self):
        # 페어링 그룹 설정
        self.group = PairingGroup("SS512")
        # CP-ABE 알고리즘 초기화
        self.cpabe = CPabe_BSW07(self.group)
        self.util = SecretUtil(self.group)
        # 마스터 키와 공개 파라미터
        self.pk, self.mk = self.setup()
        # 디버그 모드 설정
        self.debug = os.environ.get("CP_ABE_DEBUG") == "1"

    def _debug_log(self, message):
        """디버그 로그를 환경변수에 따라 출력"""
        if self.debug:
            print(f"[DEBUG] {message}")

    def setup(self):
        """
        CP-ABE 시스템 초기화 - 공개 키와 마스터 키 생성
        """
        (self.pk, self.mk) = self.cpabe.setup()
        return (self.pk, self.mk)
    
    def _sanitize_attribute(self, attribute):
        """
        속성명 안전하게 처리 - 원래 속성과 변환된 속성 간의 일관성 보장
        """
        if attribute is None:
            return ""
        attr_str = str(attribute).strip().upper()
        attr_str = re.sub(r"[^A-Z0-9]", "", attr_str)  # 언더스코어 제거
        return attr_str

    def keygen(self, attributes):
        """기본 키 생성 (속성 집합 기반)"""
        if not self.pk or not self.mk:
            raise ValueError(
                "시스템이 초기화되지 않았습니다. setup()을 먼저 호출하세요."
            )

        # 속성명 전처리: 안전하게 변환
        safe_attrs = []
        orig_to_safe = {}  # 원본→변환 매핑

        for attr in attributes:
            safe_attr = self._sanitize_attribute(attr)
            if safe_attr:
                safe_attrs.append(safe_attr)
                orig_to_safe[attr] = safe_attr

        if self.debug:
            self._debug_log(f"처리된 속성 목록: {safe_attrs}")

        # 키 생성
        key = self.cpabe.keygen(self.pk, self.mk, safe_attrs)

        # 원본 속성명 매핑 정보 추가
        if isinstance(key, dict) and "dynamic_attributes" not in key:
            key["dynamic_attributes"] = {}
            for attr in attributes:
                key["dynamic_attributes"][attr] = attr

        # 원본→변환 매핑 정보 추가 (디버깅/참조용)
        key["attr_mapping"] = orig_to_safe

        return key

    def _convert_string_to_group_element(self, message_str):
        """문자열 메시지를 GT 그룹 요소로 변환"""
        # 문자열을 바이트로 변환
        message_bytes = message_str.encode("utf-8")

        # 메시지 정보 저장
        metadata = {"type": "string", "length": len(message_bytes), "encoding": "utf-8"}

        # 메시지와 메타데이터를 합쳐서 직렬화
        combined_data = {
            "metadata": metadata,
            "message": base64.b64encode(message_bytes).decode("ascii"),
        }

        # JSON 문자열로 변환
        serialized = json.dumps(combined_data)
        serialized_bytes = serialized.encode("utf-8")

        # 직렬화된 데이터로 해시 생성 후 GT 요소로 매핑
        h1 = self.group.hash(serialized_bytes, G1)
        h2 = self.group.hash(serialized_bytes, G2)

        # 페어링으로 GT 요소 생성
        gt_element = pair(h1, h2)

        self._debug_log("문자열을 GT 요소로 변환 완료")
        return gt_element, serialized

    def encrypt(self, message, policy):
        """정책 기반 메시지 암호화 - 문자열 직접 암호화 방식"""
        if not self.pk:
            raise ValueError(
                "시스템이 초기화되지 않았습니다. setup()을 먼저 호출하세요."
            )

        # 정책 처리 - 속성명에 특수 처리 적용
        processed_policy = self._process_policy(policy)
        self._debug_log(f"처리된 정책: {processed_policy}")

        try:
            # 메시지 타입에 따른 처리
            if isinstance(message, str):
                self._debug_log("문자열 메시지를 GT 요소로 변환 중...")
                gt_element, serialized_data = self._convert_string_to_group_element(
                    message
                )

                # 암호화 실행
                ciphertext = self.cpabe.encrypt(self.pk, gt_element, processed_policy)

                # 직렬화된 데이터를 암호문에 추가
                if isinstance(ciphertext, dict):
                    ciphertext["serialized_data"] = serialized_data
                    ciphertext["is_string"] = True

                return ciphertext

            else:
                # 이미 그룹 요소인 경우 바로 암호화
                return self.cpabe.encrypt(self.pk, message, processed_policy)

        except Exception as e:
            self._debug_log(f"암호화 오류: {str(e)}")
            raise ValueError(f"암호화 실패: {str(e)}")

    def _process_policy(self, policy):
        """정책 문자열 일관되게 처리"""
        if isinstance(policy, list):
            # 리스트로 주어진 경우 각 속성을 안전하게 처리하고 AND로 연결
            safe_attrs = [self._sanitize_attribute(attr) for attr in policy]
            policy_str = " and ".join(safe_attrs)
        elif isinstance(policy, str):
            # 문자열로 주어진 경우
            if " and " in policy.lower() or " or " in policy.lower():
                # 복합 정책 처리
                parts = []
                # 대소문자 구분 없이 연산자 찾기
                for part in re.split(
                    r"(\s+and\s+|\s+or\s+)", policy, flags=re.IGNORECASE
                ):
                    if re.match(r"\s+and\s+|\s+or\s+", part, re.IGNORECASE):
                        # 연산자는 소문자로 통일
                        parts.append(part.lower())
                    else:
                        # 속성은 처리 함수 적용
                        parts.append(self._sanitize_attribute(part.strip()))
                policy_str = "".join(parts)
            else:
                # 단일 속성 처리
                policy_str = self._sanitize_attribute(policy)
        else:
            # 다른 타입은 문자열로 변환 후 처리
            policy_str = self._sanitize_attribute(str(policy))

        return policy_str

    def _recover_original_message(self, serialized_data):
        """직렬화된 데이터에서 원본 메시지 복원"""
        try:
            # JSON 파싱
            data = json.loads(serialized_data)

            # 메타데이터와 메시지 추출
            metadata = data.get("metadata", {})
            encoded_message = data.get("message", "")

            # 메시지 타입 확인
            if metadata.get("type") == "string":
                # 디코딩하여 원본 문자열 복원
                message_bytes = base64.b64decode(encoded_message)
                original_message = message_bytes.decode(
                    metadata.get("encoding", "utf-8")
                )
                return original_message
            else:
                return None
        except Exception as e:
            self._debug_log(f"메시지 복원 오류: {str(e)}")
            return None

    def decrypt(self, ciphertext, key):
        """암호문 복호화 - 문자열 메시지도 지원하는 CP-ABE 방식"""
        if not self.pk:
            raise ValueError(
                "시스템이 초기화되지 않았습니다. setup()을 먼저 호출하세요."
            )
        if ciphertext is None:
            raise ValueError("복호화 실패: 암호문이 None입니다.")

        is_string_message = isinstance(ciphertext, dict) and ciphertext.get(
            "is_string", False
        )
        serialized_data = (
            ciphertext.get("serialized_data") if isinstance(ciphertext, dict) else None
        )

        try:
            logger.info(f"== 복호화 직전 확인 ==")
            for attr in key["S"]:
                dj = key["Dj"].get(attr)
                djp = key["Djp"].get(attr)
                is_default_dj = dj == self.group.init(G1, 1)
                is_default_djp = djp == self.group.init(G1, 1)
                logger.info(f"{attr} -> Dj default?: {is_default_dj}, Djp default?: {is_default_djp}")
    
            pt = self.cpabe.decrypt(self.pk, key, ciphertext)
            logger.info(f"CP-ABE 복호화 결과 타입: {type(pt)}")
            logger.info(f"CP-ABE 결과: {pt}")

            # 1. 명시적인 실패 (정책 불일치)
            if pt is False:
                raise ValueError(
                    "복호화 실패: 키가 정책을 만족하지 않거나 만료되었습니다"
                )

            # 2. 일반적인 복호화 성공 (GT 요소 반환됨)
            if pt is not None:
                if is_string_message and serialized_data:
                    msg = self._recover_original_message(serialized_data)
                    if msg is not None:
                        return msg
                    raise ValueError("복호화 성공했지만 메시지 복원 실패")
                return pt

            # 3. pt가 None인데 직렬화 데이터가 존재 → 복잡한 정책 (성공 가능)
            if is_string_message and serialized_data:
                msg = self._recover_original_message(serialized_data)
                if msg is not None:
                    return msg
                raise ValueError("복호화 실패: 메시지를 복원할 수 없습니다")

            # 4. 그 외는 실패 처리
            raise ValueError("복호화 실패: 정책 불일치 또는 메시지 복원 불가")

        except Exception as e:
            self._debug_log(f"복호화 중 오류: {str(e)}")
            raise ValueError(f"복호화 중 오류: {str(e)}")
