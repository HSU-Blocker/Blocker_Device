# Blocker_Device

## 프로젝트 구조
```
├── backend/          # 백엔드 API 서버
├── blockchain/       # 블록체인 컨트랙트 설정
├── client/          # IoT 디바이스 클라이언트
├── crypto/          # 암호화 관련 모듈
└── ipfs/           # IPFS 관련 기능
```

## 주요 기능

### 디바이스 업데이트 프로세스
1. 블록체인에서 새로운 업데이트 이벤트 감지
2. IPFS에서 암호화된 업데이트 파일(Es) 다운로드
3. 해시값 검증 (hEbj)
4. CP-ABE로 암호화된 대칭키(Ec) 복호화하여 대칭키(kbj) 획득
5. 대칭키로 업데이트 파일 복호화하여 원본 파일(bj) 획득
6. 업데이트 설치 및 블록체인에 설치 완료 기록

## 실행

Docker 컨테이너 실행
```bash
docker-compose up --build
```

