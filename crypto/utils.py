from sha3_utils import SHA3Utils # 외부 모듈
from ecdsa_utils import ECDSAUtils
from cpabe_crypto import CPABECrypto
from aes_crypto import AESCrypto

# ecdsa_utils.py def verify_signature (init 필요 )
def verify_signature(message, signature, ecdsa_utils: ECDSAUtils) -> bool:
    """
    :param message: 서명 검증 대상(um 등). dict 형태가 일반적이며 ECDSAUtils에서 json.dumps로 처리
    :param signature: 서명
    :param ecdsa_utils: ECDSAUtils 인스턴스 (공개키 포함)
    :return: 검증 성공(True) / 실패(False)
    """
    return ecdsa_utils.verify_signature(message, signature)

# sha3_utils.py def verify_sha3_hash
def compute_sha3_hash(file_path: str) -> str:
    """
    :param file_path: 해시를 계산할 파일 경로
    :return: 16진수 문자열 형태의 SHA3-256 해시
    """
    return SHA3Utils.compute_sha3_hash(file_path)



# decrypt_service.py def decrypt_and_retrieve 통합 -> ipfs에서 받은 파일의 이름을 넣도록 되어있음 
def cpabe_decrypt_key(encrypted_key, device_sk, cpabe_instance: CPABECrypto):
    """
    CP-ABE 복호화 (AES 키 kbj 복원)
    :param encrypted_key: CP-ABE로 암호화된 AES 키 (직렬화된 dict 형태)
    :param device_sk: 디바이스(사용자) CP-ABE 개인키
    :param cpabe_instance: CPABECrypto 인스턴스 (이미 초기화된)
    :return: 복호화된 AES 키 (bytes 등)
    """
    kbj = cpabe_instance.decrypt(device_sk, encrypted_key)
    if kbj is None:
        print("CP-ABE 복호화 실패!")
        return None
    
    return kbj

def aes_decrypt_file(input_file: str, aes_key: bytes, output_file: str) -> str:
    """
    bj <- Ds(bj, kbj)
    AES(CBC)로 암호화된 input_file을 aes_key(kbj)로 복호화 → output_file에 저장
    """
    data = AESCrypto.read_data_from_file(input_file)
    aes = AESCrypto(aes_key)
    decrypted_data = aes.decrypt(data)
    AESCrypto.save_data_to_file(decrypted_data, output_file)
    return output_file
