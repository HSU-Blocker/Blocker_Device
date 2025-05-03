import time
import math
from abc import ABC, abstractmethod


class FadingFunction(ABC):
    """
    페이딩 함수 추상 기본 클래스

    논문에서 설명한 fading function의 기본 인터페이스를 정의합니다.
    페이딩 함수는 시간이 지남에 따라 속성 값을 변화시킵니다.
    시간 기반 접근 제어를 구현하는 데 사용됩니다.
    """

    def __init__(self, attribute_name):
        """
        페이딩 함수 초기화
        
        Args:
            attribute_name (str): 이 함수가 적용될 속성의 이름
                                 (예: 'subscription', 'location' 등)
        """
        self.attribute_name = attribute_name
        self.base_time = time.time()  # 기준 시간 (페이딩 시작 시간)

    @abstractmethod
    def compute_current_value(self, current_time=None):
        """
        현재 시간 기준으로 속성 값 계산
        
        Args:
            current_time (float, optional): 계산 기준 시간 (None인 경우 현재 시간 사용)
            
        Returns:
            str: 현재 시간에 해당하는 속성 값
        """
        pass

    @abstractmethod
    def is_valid(self, attribute_value, current_time=None):
        """
        주어진 속성 값이 현재 시간에 유효한지 확인
        
        Args:
            attribute_value (str): 확인할 속성 값
            current_time (float, optional): 확인 기준 시간 (None인 경우 현재 시간 사용)
            
        Returns:
            bool: 속성이 유효한 경우 True, 아니면 False
        """
        pass


class LinearFadingFunction(FadingFunction):
    """
    선형 페이딩 함수 - 일정 시간마다 값이 증가
    
    지정된 lifetime_seconds마다 속성 값이 순차적으로 변경됩니다.
    예: attribute_0, attribute_1, attribute_2, ...
    
    사용 사례:
    - 정기적으로 갱신되는 구독 속성
    - 일정 주기로 변경되는 접근 토큰
    """

    def __init__(self, attribute_name, lifetime_seconds):
        """
        선형 페이딩 함수 초기화
        
        Args:
            attribute_name (str): 이 함수가 적용될 속성의 이름
            lifetime_seconds (int): 속성 값이 변경되는 주기(초 단위)
        """
        super().__init__(attribute_name)
        self.lifetime_seconds = lifetime_seconds

    def compute_current_value(self, current_time=None):
        """
        현재 시간 기준으로 속성 값 계산
        
        Args:
            current_time (float, optional): 계산 기준 시간
            
        Returns:
            str: "{속성명}_{간격번호}" 형태의 현재 속성 값
                 예: "subscription_2"는 2번째 간격에 해당하는 구독 속성
        """
        if current_time is None:
            current_time = time.time()

        # 기준 시간으로부터 경과된 시간 계산
        time_diff = current_time - self.base_time
        # 경과 시간에 따른 간격(interval) 결정 
        interval = math.floor(time_diff / self.lifetime_seconds)

        # 시간에 따라 선형적으로 증가하는 값 계산
        current_value = f"{self.attribute_name}_{interval}"
        return current_value

    def is_valid(self, attribute_value, current_time=None):
        """
        주어진 속성 값이 현재 시간에 유효한지 확인
        
        Args:
            attribute_value (str): 확인할 속성 값 (예: "subscription_2")
            current_time (float, optional): 확인 기준 시간
            
        Returns:
            bool: 주어진 속성 값이 현재 계산된 값과 정확히 일치하면 True
        """
        current_value = self.compute_current_value(current_time)
        return attribute_value == current_value


class StepFadingFunction(FadingFunction):
    """
    계단식 페이딩 함수 - 특정 임계값에 도달할 때마다 값이 변화
    
    전체 수명을 여러 단계(steps)로 나누어 각 단계마다 값이 변화합니다.
    각 단계는 동일한 시간 간격을 가집니다.
    
    사용 사례:
    - 등급이 점차 하락하는 접근 권한
    - 단계별로 제한되는 기능
    """

    def __init__(self, attribute_name, lifetime_seconds, steps=5):
        """
        계단식 페이딩 함수 초기화
        
        Args:
            attribute_name (str): 이 함수가 적용될 속성의 이름
            lifetime_seconds (int): 전체 수명(초 단위)
            steps (int, optional): 단계 수(기본값: 5)
        """
        super().__init__(attribute_name)
        self.lifetime_seconds = lifetime_seconds
        self.steps = steps  # 총 단계 수

    def compute_current_value(self, current_time=None):
        """
        현재 시간 기준으로 속성 값 계산
        
        Args:
            current_time (float, optional): 계산 기준 시간
            
        Returns:
            str: "{속성명}_step{단계번호}" 형태의 현재 속성 값
                 예: "access_step2"는 2단계에 해당하는 접근 속성
        """
        if current_time is None:
            current_time = time.time()

        # 기준 시간으로부터 경과된 시간 계산
        time_diff = current_time - self.base_time
        # 각 단계의 지속 시간 계산
        step_size = self.lifetime_seconds / self.steps
        # 현재 단계 결정 
        current_step = math.floor(time_diff / step_size)

        # 계단식으로 변화하는 속성값 계산
        current_value = f"{self.attribute_name}_step{current_step}"
        return current_value

    def is_valid(self, attribute_value, current_time=None):
        """
        주어진 속성 값이 현재 시간에 유효한지 확인
        
        Args:
            attribute_value (str): 확인할 속성 값 (예: "access_step2")
            current_time (float, optional): 확인 기준 시간
            
        Returns:
            bool: 주어진 속성 값이 현재 계산된 값과 정확히 일치하면 True
        """
        current_value = self.compute_current_value(current_time)
        return attribute_value == current_value


class LocationFadingFunction(FadingFunction):
    """
    위치 속성을 위한 특수 페이딩 함수
    
    위치 정보는 ID와 세분화 수준(granularity)에 따라 다르게 페이딩됩니다.
    세분화 수준이 높을수록(값이 클수록) 더 빠르게 페이딩됩니다.
    
    사용 사례:
    - 위치 기반 접근 제어
    - 상세한 위치 정보일수록 빨리 만료되도록 설정
    """

    def __init__(self, location_id, granularity, lifetime_seconds):
        """
        위치 페이딩 함수 초기화
        
        Args:
            location_id (str): 위치 식별자
            granularity (int): 세분화 수준 (1=대략적, 2=중간, 3=상세)
                              값이 클수록 더 빨리 페이딩됨
            lifetime_seconds (int): 기본 수명(초 단위)
        """
        super().__init__(f"loc_{location_id}_{granularity}")
        self.location_id = location_id
        self.granularity = granularity  # 1=coarse(대략적), 2=medium(중간), 3=fine(상세)
        self.lifetime_seconds = lifetime_seconds

    def compute_current_value(self, current_time=None):
        """
        현재 시간 기준으로 위치 속성 값 계산
        
        Args:
            current_time (float, optional): 계산 기준 시간
            
        Returns:
            str: "loc_{위치ID}_{세분화수준}_{간격번호}" 형태의 현재 속성 값
                 예: "loc_seoul_2_1"은 'seoul' 위치의 중간 세분화 수준에서 1번 간격
        """
        if current_time is None:
            current_time = time.time()

        # 기준 시간으로부터 경과된 시간 계산
        time_diff = current_time - self.base_time
        # 세분화 수준에 따라 lifetime 조정 (세분화가 높을수록 수명이 짧아짐)
        adjusted_lifetime = self.lifetime_seconds / self.granularity
        # 조정된 lifetime에 따른 간격 계산
        interval = math.floor(time_diff / adjusted_lifetime)

        # 위치 속성의 현재 값 계산
        current_value = f"loc_{self.location_id}_{self.granularity}_{interval}"
        return current_value

    def is_valid(self, attribute_value, current_time=None):
        """
        주어진 위치 속성 값이 현재 시간에 유효한지 확인
        
        Args:
            attribute_value (str): 확인할 위치 속성 값
            current_time (float, optional): 확인 기준 시간
            
        Returns:
            bool: 주어진 속성 값이 현재 계산된 값과 정확히 일치하면 True
        """
        current_value = self.compute_current_value(current_time)
        return attribute_value == current_value


class HardExpiryFadingFunction(FadingFunction):
    """
    Hard Expiry 페이딩 함수 - 특정 시간이 지나면 무조건 만료됨
    
    지정된 lifetime 이후에는 무조건 만료되며, 최대 갱신 횟수를 제한할 수 있습니다.
    최대 갱신 횟수를 초과하면 영구적으로 만료된 상태가 됩니다.
    
    사용 사례:
    - 엄격한 시간 제한이 필요한 임시 접근 권한
    - 특정 횟수만 갱신할 수 있는 한시적 속성
    """

    def __init__(self, attribute_name, lifetime_seconds, max_renewals=None):
        """
        Hard Expiry 페이딩 함수 초기화
        
        Args:
            attribute_name (str): 이 함수가 적용될 속성의 이름
            lifetime_seconds (int): 속성의 수명(초 단위)
            max_renewals (int, optional): 최대 갱신 횟수, None이면 무제한
        """
        super().__init__(attribute_name)
        self.lifetime_seconds = lifetime_seconds
        self.max_renewals = max_renewals  # 최대 갱신 횟수

    def compute_current_value(self, current_time=None):
        """
        현재 시간 기준으로 속성 값 계산
        
        Args:
            current_time (float, optional): 계산 기준 시간
            
        Returns:
            str: "{속성명}_{간격번호}" 형태의 현재 속성 값 또는
                 최대 갱신 횟수 초과 시 "{속성명}_expired"
        """
        if current_time is None:
            current_time = time.time()

        # 경과 시간 계산
        time_diff = current_time - self.base_time

        # 간격 계산
        interval = math.floor(time_diff / self.lifetime_seconds)

        # 최대 갱신 횟수 초과 체크
        if self.max_renewals is not None and interval > self.max_renewals:
            # 만료된 속성 값 반환
            return f"{self.attribute_name}_expired"

        # 정상 속성 값 반환
        return f"{self.attribute_name}_{interval}"

    def is_valid(self, attribute_value, current_time=None):
        """
        주어진 속성 값이 현재 시간에 유효한지 확인
        
        Args:
            attribute_value (str): 확인할 속성 값
            current_time (float, optional): 확인 기준 시간
            
        Returns:
            bool: 유효한 속성이면 True, 만료되었거나 불일치하면 False
        """
        current_value = self.compute_current_value(current_time)
        # expired 값은 항상 유효하지 않음
        if current_value.endswith("_expired") or attribute_value.endswith("_expired"):
            return False
        return attribute_value == current_value
