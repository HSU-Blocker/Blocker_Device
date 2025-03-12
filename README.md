# Blocker_Device

<디바이스>
1. 디바이스에서 업데이트 메시지 & 서명 검증 (블록체인 관련 부분은 일단 생략)
2. hEbj & IPFS에서 다운 받은 Es(bj, kbj) 해시값 비교 (일단 IPFS 생략, 파일 경로를 파라미터로 받음)
3. 디바이스에서 복호화 수행 - kbj <- Dc(PKc, kbj, A) , bj <- Ds(bj, kbj)
