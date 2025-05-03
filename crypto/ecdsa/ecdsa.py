from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

class ECDSATools:

    @staticmethod
    def sign_message(uid, ipfs_hash, encrypted_key, hash_of_update, eth_private_key):
        """Ethereum private key로 메시지 서명"""
        """Solidity에서 사용하는 방식과 동일하게 서명 (abi.encodePacked 대응)"""
        # 1. 바이트로 인코딩해서 붙이기
        message_bytes = (
            uid.encode('utf-8') +
            ipfs_hash.encode('utf-8') +
            encrypted_key.encode('utf-8') +
            hash_of_update.encode('utf-8')
        )

        # 2. keccak256 해시
        message_hash = Web3.keccak(message_bytes)

        # 3. Ethereum Signed Message prefix 붙이기
        eth_message = encode_defunct(message_hash)

        # 4. 서명
        signed = Account.sign_message(eth_message, private_key=eth_private_key)
        return signed.signature  # 65 bytes