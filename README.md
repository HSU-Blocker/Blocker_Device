# Blocker_Device  

## Overview  
This repository represents the device module of a blockchain-based IoT software update platform.
When the manufacturer registers a new software update on the blockchain, the device detects the event, purchases the update, downloads the encrypted update package from IPFS, verifies its integrity, decrypts it, and installs it. The installation status is then recorded on the blockchain.

### Device Update Process  
1. Detect a new software update event on the blockchain and receive the update notification
2. Purchase the update package
3. Download the encrypted update file (Es) from IPFS
4. Compute the SHA3-256 hash of the file and verify it against the registered reference hash (hEbj)
5. Decrypt the symmetric key (kbj) from the CP-ABE encrypted key (Ec)
6. Derive the AES-256 key by serializing kbj and applying SHA-256 hashing, then decrypt the update file to restore the original file (bj)
7. Install the verified update on the device and record the installation result on the blockchain via smart contract

## Development Environment  
<img width="742" height="380" alt="image" src="https://github.com/user-attachments/assets/8f67a5bd-9917-4593-90d0-11d954df52f7" />

- **AIoT AutoCar Prime X**
  - AiOT AutoCar Prime X is equipped with the high-performance AI module Nvidia Jetson Xavier NX, providing sufficient computing power for artificial intelligence applications. It comes with the Pop.AI library, which allows learners to easily explore AI concepts and apply them to the car through various practical exercises and projects. The platform supports diverse sensors and peripherals such as cameras, microphones, 6-axis sensors, vehicle chassis, and speakers, enabling users to experiment with a wide range of AI-driven ideas.
  - In our project, we utilized this car as the IoT device to allow device owners to subscribe to and implement the manufacturer’s software updates, specifically focusing on autonomous driving functions. While we demonstrated our system on the AutoCar Prime X, the service is also designed to be compatible with other IoT devices such as Raspberry Pi.
- ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)  
- ![Ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=flat&logo=ubuntu&logoColor=white)  
- ![Python](https://img.shields.io/badge/Python_3.10--slim_(arm64)-3776AB?style=flat&logo=python&logoColor=white)  Configured a Docker-based Ubuntu environment using the **Python 3.10-slim (arm64)** image
- ![VSCode](https://img.shields.io/badge/Visual_Studio_Code-007ACC?style=flat&logo=visualstudiocode&logoColor=white)  

## Technology Stack
- ![Blockchain](https://img.shields.io/badge/Blockchain-121D33?style=flat&logo=blockchaindotcom&logoColor=white)  Manage update IDs, hashes, and encrypted keys securely on the blockchain  

- ![Smart Contract](https://img.shields.io/badge/Smart_Contract-2C3E50?style=flat&logo=ethereum&logoColor=white)  Establish agreements between manufacturer and device, automating update management  

- ![ECDSA](https://img.shields.io/badge/ECDSA_Signature-34495E?style=flat&logo=lock&logoColor=white)  Verify update request and installation integrity using **ECDSA signature validation**  

- ![Web3](https://img.shields.io/badge/Web3-F16822?style=flat&logo=web3dotjs&logoColor=white)  Interact with the blockchain using Web3 libraries  

- ![IPFS](https://img.shields.io/badge/IPFS_File_Download-65C2CB?style=flat&logo=ipfs&logoColor=white)  Download **encrypted update files** from IPFS with distributed storage support  

- ![AES-256](https://img.shields.io/badge/AES--256_Decryption-006699?style=flat&logo=databricks&logoColor=white)  Decrypt update files using AES-256 to retrieve the original file  

- ![CP-ABE](https://img.shields.io/badge/CP--ABE_Key_Management-6C3483?style=flat&logo=academia&logoColor=white)  
  Decrypt CP-ABE–encrypted update keys to enforce access control policies.  
  Implemented using the [Charm-Crypto](https://github.com/JHUISI/charm) library for advanced cryptographic 

- ![SHA3-256](https://img.shields.io/badge/SHA3--256_Hash_Verification-117A65?style=flat&logo=datadog&logoColor=white)  Verify file integrity by comparing **SHA3-256 hash** with blockchain values  

- ![WebSocket](https://img.shields.io/badge/WebSocket_Event_Listener-008080?style=flat&logo=socketdotio&logoColor=white)  Detect blockchain events in real-time for update monitoring  

- ![Flask](https://img.shields.io/badge/Flask_Device_Backend-000000?style=flat&logo=flask&logoColor=white)  Device backend server built with Flask  

## Installation
See [INSTALL.md](./INSTALL.md) for installation and usage instructions.

## Directory Structure
```
backend/
├── api.py                      # Backend API entry point
blockchain/
└── registry_address.json       # Blockchain registry address/config
client/
├── device_client.py            # Device client runner script
└── keys/
    ├── device_secret_key_file.bin  # Device private key
    └── public_key.bin              # Debice Manufacturer Public key
crypto/
├── cpabe/
│   └── cpabe.py                 # CP-ABE (attribute-based encryption) implementation
├── hash/
│   └── hash.py                  # Hash utilities
└── symmetric/
    └── symmetric.py             # Symmetric-key encryption utilities
ipfs/
└── download/
    └── download.py             # IPFS download logic
Dockerfile                      # Root application Docker build config
docker-compose.yml              # Service orchestration config
requirements.txt                # Python dependencies list
```

## License

This project is licensed under the MIT License. See [LICENSE](./LICENSE) for details.

---

Contributions and questions are always welcome through Issues and Pull Requests.  
For detailed contribution guidelines, please refer to the following file:  
[Contribution Guide](https://github.com/HSU-Blocker/Blocker_Device?tab=contributing-ov-file)
