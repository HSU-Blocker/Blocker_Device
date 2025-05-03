from .iot_cpabe import IoTCPABE
from charm.toolbox.pairinggroup import ZR, G1
from datetime import datetime
import time
import uuid
import json
import base64
from charm.core.engine.util import objectToBytes, bytesToObject
import logging
import re
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))  # KST 정의

class DynamicCPABE(IoTCPABE):
    """
    동적 속성 관리 기능을 갖춘 CP-ABE 구현
    - 정적 속성: 모델, 일련번호 (변하지 않음)
    - 동적 속성: 구독, 보증 (시간에 따라 자동 변경됨)
    """

    def __init__(self):
        super().__init__()
        self.user_records = {}  # 사용자 레코드
        self.fading_functions = {}  # 페이딩 함수
    
    def _sanitize_attribute(self, attribute):
        """
        속성명 안전하게 처리 - 원래 속성과 변환된 속성 간의 일관성 보장
        """
        if attribute is None:
            return ""
        attr_str = str(attribute).strip().upper()
        attr_str = re.sub(r"[^A-Z0-9]", "", attr_str)  # 언더스코어 제거
        return attr_str


    def _debug_log(self, message):
        """
        디버그 로그 출력
        """
        import os

        debug_mode = os.environ.get("CP_ABE_DEBUG") == "1"
        if debug_mode:
            print(f"[DEBUG] {message}")

    def register_fading_function(self, attribute_name, fading_function):
        """시스템에 새 페이딩 함수 등록"""
        self.fading_functions[attribute_name] = fading_function

    def create_user_record(self, user_id=None):
        """새 사용자 레코드 생성"""
        if user_id is None:
            user_id = str(uuid.uuid4())

        record = {
            "user_id": user_id,
            "random_value": self.group.random(ZR),
            "creation_time": time.time(),
            "attributes": {},
        }

        self.user_records[user_id] = record
        self._debug_log(f"사용자 레코드 생성: {user_id}")
        return user_id

    def compute_attribute_value(self, attribute_name, current_time=None):
        """페이딩 함수로 현재 속성 값 계산"""
        # 페이딩 함수가 등록되지 않은 속성은 정적 속성으로 처리
        if attribute_name not in self.fading_functions:
            return attribute_name  # 수정: 원래 속성 이름 그대로 반환 (suffix 없음)

        raw_value = self.fading_functions[attribute_name].compute_current_value(current_time)
        return self._sanitize_attribute(raw_value)
    

    def keygen_with_attributes(self, attributes, expiry_attributes=None):
        """
        정적 및 동적 속성을 모두 포함한 키 생성
        Args:
            attributes: 정적 속성 리스트
            expiry_attributes: 동적 속성 딕셔너리 {속성이름: 만료일자}
        """
        # 기본 속성 설정
        all_attributes = attributes.copy()

        # 만료 속성 정보 저장
        expiry_info = {}

        # 만료 속성이 있는 경우 처리
        if expiry_attributes:
            for attr, expiry in expiry_attributes.items():
                # 타임스탬프로 직접 주어진 경우
                if isinstance(expiry, int) or isinstance(expiry, float):
                    expiry_timestamp = float(expiry)
                else:
                    try:
                        # 시분초 포함 날짜 파싱 → KST로 설정
                        dt = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                        dt_kst = dt.replace(tzinfo=KST)
                        expiry_timestamp = dt_kst.timestamp()
                        logger.info(f"[KST 변환] {attr} -> {expiry} → {expiry_timestamp}")
                    except ValueError:
                        try:
                            # 날짜만 있는 경우도 KST로 설정
                            dt = datetime.strptime(expiry, "%Y-%m-%d")
                            dt_kst = dt.replace(tzinfo=KST)
                            expiry_timestamp = dt_kst.timestamp()
                        except ValueError:
                            raise ValueError(f"지원되지 않는 날짜 형식: {expiry}")

                # 속성 목록에 동적 속성 추가
                all_attributes.append(attr)
                expiry_info[attr] = expiry_timestamp

        # 키 생성
        key = self.cpabe.keygen(self.pk, self.mk, all_attributes)

        if isinstance(key, dict):
            key["orig_attributes"] = all_attributes
            key["expiry_info"] = expiry_info
            key["dynamic_attributes"] = {}
            for attr in attributes:
                key["dynamic_attributes"][attr] = attr
            for attr in expiry_info:
                key["dynamic_attributes"][attr] = attr

        return key

    
    # def keygen_with_attributes(self, attributes, expiry_attributes=None):
        # """
        # 정적 및 동적 속성을 모두 포함한 키 생성

        # Args:
        #     attributes: 정적 속성 리스트
        #     expiry_attributes: 동적 속성 딕셔너리 {속성이름: 만료일자}
        # """
        # # 기본 속성 설정
        # all_attributes = attributes.copy()

        # # 만료 속성 정보 저장
        # expiry_info = {}

        # # 만료 속성이 있는 경우 처리
        # if expiry_attributes:
        #     for attr, expiry in expiry_attributes.items():
        #         # 타임스탬프로 직접 주어진 경우
        #         if isinstance(expiry, int):
        #             expiry_timestamp = expiry
        #         else:
        #             # 만료일을 timestamp로 변환 - 여러 형식 지원
        #             try:
        #                 # 시분초 포함 형식 시도
        #                 expiry_timestamp = int(
        #                     datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S").timestamp()
        #                 )
        #                 logger.info(f"expiry_timestamp: {expiry_timestamp}")
        #             except ValueError:
        #                 try:
        #                     # 날짜만 있는 형식 시도
        #                     expiry_timestamp = int(
        #                         datetime.strptime(expiry, "%Y-%m-%d").timestamp()
        #                     )
        #                 except ValueError:
        #                     raise ValueError(f"지원되지 않는 날짜 형식: {expiry}")

        #         # 속성 목록에 동적 속성 추가
        #         all_attributes.append(attr)
        #         # 만료 정보 저장
        #         expiry_info[attr] = expiry_timestamp

        # # 키 생성
        # key = self.cpabe.keygen(self.pk, self.mk, all_attributes)

        # # 키에 메타데이터 추가
        # if isinstance(key, dict):
        #     key["orig_attributes"] = all_attributes
        #     key["expiry_info"] = expiry_info
        #     # 동적 속성 현재값 저장
        #     key["dynamic_attributes"] = {}
        #     for attr in attributes:
        #         key["dynamic_attributes"][attr] = attr  # 정적 속성은 그대로
        #     for attr in expiry_info:
        #         key["dynamic_attributes"][attr] = attr  # 동적 속성 초기값

        # return key

        
    def keygen_with_dynamic_attributes(self, user_id, attributes: dict):
        """
        동적 속성이 포함된 키 생성 (정적 + 동적)
        attributes: {"model": "ABC123", "serial": "SN12345", "subscription": 180}
        """
        if not self.pk or not self.mk:
            self.setup()

        if user_id not in self.user_records:
            raise ValueError(f"알 수 없는 사용자 ID: {user_id}")

        base_attributes = []
        dynamic_attrs = {}

        # 동적/정적 속성 구분
        for attr_name, value in attributes.items():
            attr_lower = attr_name.lower()
            if attr_lower in self.fading_functions:
                self.fading_functions[attr_name].base_time = time.time()
                
                current_value = self.compute_attribute_value(attr_lower)
                sanitized = self._sanitize_attribute(current_value)
                dynamic_attrs[attr_lower] = sanitized
                base_attributes.append(sanitized)
            else:
                base_attributes.append(self._sanitize_attribute(value))

        # 키 생성
        key = self.keygen(base_attributes)

        if isinstance(key, dict):
            key["user_id"] = user_id
            key["issue_time"] = time.time()
            key["dynamic_attributes"] = {}
            key["expiry_info"] = {}
            key["attr_mapping"] = {}
            key["S"] = key.get("S", [])
            key["update_history"] = []

            # 정적 속성 처리 (단지 attr_mapping, S에만 반영)
            for attr_name, value in attributes.items():
                if attr_name.lower() not in self.fading_functions:
                    sanitized = self._sanitize_attribute(value)
                    key["attr_mapping"][attr_name] = sanitized
                    if sanitized not in key["S"]:
                        key["S"].append(sanitized)

            # 동적 속성만 dynamic_attributes에 저장
            for attr_name, current_value in dynamic_attrs.items():
                key["dynamic_attributes"][attr_name] = current_value
                key["attr_mapping"][attr_name] = current_value
                if current_value not in key["S"]:
                    key["S"].append(current_value)
                key["expiry_info"][attr_name] = {
                    "expiry_time": self.get_attribute_expiry_time(attr_name),
                    "max_renewals": self.get_max_renewals(attr_name),
                    "current_renewals": 0,
                }

            self._debug_log(f"[키 생성 완료] 동적 속성: {dynamic_attrs}, S: {key['S']}")

        return key


    def keygen(self, attributes):
        """기본 키 생성 메서드 오버라이드 - 추가 메타데이터 포함"""
        key = super().keygen(attributes)

        # 기본 키에 필요한 메타데이터 추가
        if isinstance(key, dict):
            # 동적 속성 메타데이터 추가
            key["dynamic_attributes"] = {attr: attr for attr in attributes}
            # 빈 만료 정보 추가
            key["expiry_info"] = {}
            # 발급 시간 추가
            key["issue_time"] = time.time()
            
            # 복호화 필수 컴포넌트 존재 보장
            if "Dj" not in key:
                key["Dj"] = {}
            if "Djp" not in key:
                key["Djp"] = {}
        return key

    def check_key_validity(self, key):
        # current_time = time.time() + 9 * 360
        current_time = time.time()
        valid_attrs = []
        expired_attrs = []

        for attr_name, attr_value in key["dynamic_attributes"].items():
            # 만료 시간 기준 먼저 체크
            expiry_data = key.get("expiry_info", {}).get(attr_name)
            if expiry_data:
                expiry_time = float(expiry_data.get("expiry_time"))
                logger.info(f"[유효성 검사] 현재 시간: {current_time}, {attr_name} 만료 시각: {expiry_time}, Δ={current_time - expiry_time}")
                if current_time > expiry_time:
                    logger.info(f"{attr_name} 만료됨: now={current_time}, expiry={expiry_time}")
                    expired_attrs.append(attr_name)
                    continue

            # 값 비교 (fallback)
            if attr_name in self.fading_functions:
                expected_value = self.compute_attribute_value(attr_name)
                if attr_value == expected_value:
                    valid_attrs.append(attr_name)
                else:
                    expired_attrs.append(attr_name)
            else:
                valid_attrs.append(attr_name)

        is_valid = len(expired_attrs) == 0
        return {
            "valid": is_valid,
            "valid_attrs": valid_attrs,
            "expired_attrs": expired_attrs,
        }

    def update_attribute(self, user_id, attribute_name):
        """특정 속성 갱신"""
        if attribute_name not in self.fading_functions:
            raise ValueError(f"동적 속성이 아닙니다: {attribute_name}")

        # 속성의 새 값 계산
        new_value = self.compute_attribute_value(attribute_name)
        sanitized_value = self._sanitize_attribute(new_value)

        # 새 키 컴포넌트 생성
        # 속성 이름에서 현재 값을 구함
        sanitized_value = self.compute_attribute_value(attribute_name)

        # 키 생성 시에는 해당 속성의 현재 값 자체를 기준으로 생성해야 함
        new_attr_key = self.cpabe.keygen(self.pk, self.mk, [sanitized_value])

        self._debug_log(
            f"속성 갱신 - 사용자: {user_id}, 속성: {attribute_name}, 새 값: {new_value}"
        )
        # 갱신 정보 반환
        return {
            "attribute_name": attribute_name,             # 예: 'subscription'
            "attribute_value": sanitized_value,           # 예: 'SUBSCRIPTION_0'
            "attribute_key": new_attr_key,                # 해당 값으로 생성한 키 컴포넌트
            "issue_time": time.time(),
        }

    def merge_attribute_to_key(self, key, new_attr):
        """
        기존 키에 새 속성 병합 (부분 키 갱신)
        """
        if not isinstance(key, dict) or "dynamic_attributes" not in key:
            raise ValueError("유효하지 않은 키 형식")

        if not isinstance(new_attr, dict) or "attribute_name" not in new_attr:
            raise ValueError("유효하지 않은 속성 형식")

        # 새 키 객체 생성 (깊은 복사)
        updated_key = dict(key)

        # 복잡한 객체는 참조 복사 (charm-crypto Element 객체 등)
        for k, v in key.items():
            if k not in [
                "dynamic_attributes",
                "expiry_info",
                "update_history",
                "S",
                "attr_mapping",
            ]:
                updated_key[k] = v

        # 동적 속성 및 만료 정보 복사
        updated_key["dynamic_attributes"] = dict(key["dynamic_attributes"])
        if "expiry_info" in key:
            updated_key["expiry_info"] = dict(key["expiry_info"])
        else:
            updated_key["expiry_info"] = {}

        # 업데이트 이력 복사 및 추가
        if "update_history" in key:
            updated_key["update_history"] = list(key["update_history"])
        else:
            updated_key["update_history"] = []

        # 새 속성 정보 추가
        attr_name = new_attr["attribute_name"]
        attr_value = new_attr["attribute_value"]

        # 이전 속성 값 제거 (중복 제거)
        old_value = key["dynamic_attributes"].get(attr_name)
        old_sanitized = self._sanitize_attribute(old_value)

        if "S" in updated_key and old_sanitized in updated_key["S"]:
            updated_key["S"].remove(old_sanitized)
        if "Dj" in updated_key and old_sanitized in updated_key["Dj"]:
            del updated_key["Dj"][old_sanitized]
        if "Djp" in updated_key and old_sanitized in updated_key["Djp"]:
            del updated_key["Djp"][old_sanitized]

        # 속성 값 업데이트
        updated_key["dynamic_attributes"][attr_name] = attr_value

        # attr_mapping 복사 및 업데이트
        if "attr_mapping" in key:
            updated_key["attr_mapping"] = dict(key["attr_mapping"])
        else:
            updated_key["attr_mapping"] = {}

        # 새 동적 속성을 attr_mapping에 추가
        # 이미 sanitized된 값이므로 sanitize 하지 않고 그대로 사용
        sanitized_attr = attr_value

        # S, Dj, Djp 업데이트 시 그대로 사용
        if sanitized_attr not in updated_key["S"]:
            updated_key["S"].append(sanitized_attr)

        # 암호학적 컴포넌트 업데이트 (매우 중요 - 이 값이 제대로 설정되어야 복호화가 작동함)
        if "attribute_key" in new_attr:
            # 새로운 속성 키에서 암호학적 컴포넌트를 가져와 업데이트
            attr_key = new_attr["attribute_key"]

            if (
                "Dj" in attr_key
                and "Dj" in updated_key
                and sanitized_attr in attr_key["Dj"]
            ):
                # 새 속성 키에서 해당 속성의 Dj 값을 가져와 업데이트
                updated_key["Dj"][sanitized_attr] = attr_key["Dj"][sanitized_attr]
            elif "Dj" in updated_key:
                # 해당 속성이 새 키에 없는 경우 기본값으로 설정
                updated_key["Dj"][sanitized_attr] = self.group.init(G1, 1)

            if (
                "Djp" in attr_key
                and "Djp" in updated_key
                and sanitized_attr in attr_key["Djp"]
            ):
                # 새 속성 키에서 해당 속성의 Djp 값을 가져와 업데이트
                updated_key["Djp"][sanitized_attr] = attr_key["Djp"][sanitized_attr]
            elif "Djp" in updated_key:
                # 해당 속성이 새 키에 없는 경우 기본값으로 설정
                updated_key["Djp"][sanitized_attr] = self.group.init(G1, 1)
        else:
            # 속성 키가 제공되지 않은 경우 기본값 사용
            if "Dj" in updated_key:
                updated_key["Dj"][sanitized_attr] = self.group.init(G1, 1)
            if "Djp" in updated_key:
                updated_key["Djp"][sanitized_attr] = self.group.init(G1, 1)


        # 만료 정보 업데이트
        if "expiry_info" in new_attr and attr_name in new_attr["expiry_info"]:
            updated_key["expiry_info"][attr_name] = new_attr["expiry_info"][attr_name]

        # 갱신 횟수 증가
        if attr_name in updated_key["expiry_info"]:
            current_renewals = updated_key["expiry_info"][attr_name].get(
                "current_renewals", 0
            )
            updated_key["expiry_info"][attr_name]["current_renewals"] = (
                current_renewals + 1
            )

        # 업데이트 이력에 기록
        updated_key["update_history"].append(
            {
                "attribute": attr_name,
                "value": attr_value,
                "update_time": time.time(),
            }
        )

        self._debug_log(f"속성 병합 완료 - 속성: {attr_name}, 값: {attr_value}")
        return updated_key

    def encrypt_with_dynamic_attributes(self, msg, policy_attributes):
        """
        동적 속성을 고려하여 메시지 암호화
        """
        # 디버깅 로그 출력 여부 확인
        import os

        debug_mode = os.environ.get("CP_ABE_DEBUG") == "1"

        # 빈 정책인 경우 처리
        if not policy_attributes:
            raise ValueError("정책 속성이 비어 있습니다")

        # 정책 속성 목록 처리
        if isinstance(policy_attributes, list):
            # 속성 목록 직접 처리 - 동적 속성 현재값 계산
            transformed_policy = []
            for attr_name in policy_attributes:
                if attr_name in ["subscription", "warranty"]:
                    # 동적 속성인 경우 현재 값 계산
                    attr_value = self.compute_attribute_value(attr_name)
                    # transformed_policy.append(attr_value)
                    transformed_policy.append(self._sanitize_attribute(attr_value))
                else:
                    # 정적 속성은 그대로 사용
                    # transformed_policy.append(attr_name)
                    transformed_policy.append(self._sanitize_attribute(attr_name))

            # 조건부 로깅
            if debug_mode:
                print(f"실제 사용 정책: {transformed_policy}")

            # 암호화 수행 - IoTCPABE의 encrypt 메서드 사용
            try:
                result = self.encrypt(msg, transformed_policy)
                logger.info(f"암호화 성공 - 정책: {transformed_policy}")
                logger.info(f"CP-ABE 암호화 result: {result}")
                serialized = objectToBytes(result, self.group)
                encoded = base64.b64encode(serialized).decode("utf-8")
                return encoded
            except Exception as e:
                if debug_mode:
                    print(f"암호화 오류: {str(e)}")
                self._debug_log(f"암호화 실패 - 오류: {str(e)}")
                return None
        else:
            # 정책이 문자열이나 다른 형태인 경우
            try:
                result = self.encrypt(msg, policy_attributes)
                logger.info(f"암호화 성공 - 정책: {policy_attributes}")
                logger.info(f"CP-ABE 암호화 result: {result}")
                serialized = objectToBytes(result, self.group)
                encoded = base64.b64encode(serialized).decode("utf-8") 
                return encoded
            except Exception as e:
                if debug_mode:
                    print(f"암호화 오류: {str(e)}")
                self._debug_log(f"암호화 실패 - 오류: {str(e)}")
                return None

    def decrypt(self, ciphertext, key):
        """
        암호문 복호화 - 동적 속성 관리 개선
        """
        # base64로 인코딩된 문자열인 경우 처리
        if isinstance(ciphertext, str):
            try:
                ciphertext_bytes = base64.b64decode(ciphertext)
                ciphertext = bytesToObject(ciphertext_bytes, self.group)
                self._debug_log("base64 문자열을 복호화 가능한 객체로 디코딩 완료")
            except Exception as e:
                raise ValueError(f"base64 디코딩 실패: {e}")
                
        # dynamic_attributes에서 실제 속성값 적용
        if isinstance(key, dict) and "dynamic_attributes" in key and "S" in key:
            # 동적 속성을 속성 목록에 추가 (아직 추가되지 않은 경우)
            attr_mapping = key.get("attr_mapping", {})
            dynamic_attrs = key["dynamic_attributes"]

            # 키 유효성 검사
            validity = self.check_key_validity(key)
            logger.info(f"validity: {validity}")
            if not validity["valid"]:
                print(f"키 유효성 검사 실패: {validity['expired_attrs']}")
                self._debug_log(
                    f"복호화 실패 - 키 유효성 검사 실패: {validity['expired_attrs']}"
                )
                # 만료된 속성이 있다면 복호화 불가
                if validity["expired_attrs"]:
                    return False

        # 부모 클래스의 복호화 메서드 호출
        self._debug_log("복호화 시도")
        return super().decrypt(ciphertext, key)

    def get_attribute_expiry_time(self, attr_name):
        if attr_name in self.fading_functions:
            fading_func = self.fading_functions[attr_name]

            # base_time 기준으로 계산
            if hasattr(fading_func, "lifetime_seconds"):
                expiry_time = fading_func.base_time + fading_func.lifetime_seconds
            elif hasattr(fading_func, "lifetime"):
                expiry_time = fading_func.base_time + fading_func.lifetime
            elif hasattr(fading_func, "period"):
                expiry_time = fading_func.base_time + fading_func.period
            else:
                expiry_time = fading_func.base_time + 3600  # default 1 hour

            self._debug_log(
                f"[정확한 만료 시간 계산] {attr_name}: base={fading_func.base_time}, expiry={expiry_time}"
            )
            return expiry_time

        return time.time() + (365 * 24 * 60 * 60)

    def get_max_renewals(self, attr_name):
        """
        속성의 최대 갱신 횟수 반환
        """
        # 속성에 대한 페이딩 함수가 있는지 확인
        if attr_name in self.fading_functions:
            fading_func = self.fading_functions[attr_name]

            # HardExpiryFadingFunction은 max_renewals 속성을 갖고 있음
            if hasattr(fading_func, "max_renewals"):
                max_renewals = fading_func.max_renewals
                self._debug_log(
                    f"최대 갱신 횟수 계산 - 속성: {attr_name}, 최대 갱신 횟수: {max_renewals}"
                )
                return max_renewals

        # 기본값은 무제한 갱신 (-1)
        self._debug_log(f"최대 갱신 횟수 계산 - 속성: {attr_name}, 최대 갱신 횟수: -1")
        return -1

    def save_key_to_bin_file(self, key, group, filepath):
        with open(filepath, "wb") as f:
            f.write(objectToBytes(key, group))
        
    def load_key_from_bin_file(self, group, filepath):
        with open(filepath, "rb") as f:
            return bytesToObject(f.read(), group)

