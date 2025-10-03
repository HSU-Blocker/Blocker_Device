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

- **IoT Device**: **AIoT AutoCar Prime X**
  - AiOT AutoCar Prime X is an AI-enabled model car equipped with the Nvidia Jetson Xavier NX module, offering sufficient computing power to run advanced applications.

  - In our project, we chose this car as the IoT device because the manufacturer’s update files were designed to deliver autonomous driving services. The device was set up to subscribe to these updates, so that each update installation would add new autonomous driving features. While we demonstrated our system on the AutoCar Prime X, the service is also designed to be compatible with other IoT devices such as Raspberry Pi.
- **OS**: ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
 ![Ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=flat&logo=ubuntu&logoColor=white)  
- **Programming Language**: ![Python](https://img.shields.io/badge/Python_3.10--slim_(arm64)-3776AB?style=flat&logo=python&logoColor=white)  
  - Configured a Docker-based Ubuntu environment using the **Python 3.10-slim (arm64)** image  
- **Development Tools**: ![VSCode](https://img.shields.io/badge/Visual_Studio_Code-007ACC?style=flat&logo=visualstudiocode&logoColor=white)  

## Technology Stack
- ![Blockchain](https://img.shields.io/badge/Blockchain-121D33?style=flat&logo=blockchaindotcom&logoColor=white)  Upload **the signature, update price, version, description, hash of the encrypted file, IPFS hash, and the encrypted symmetric key** to the blockchain.

- ![Smart Contract](https://img.shields.io/badge/Smart_Contract-2C3E50?style=flat&logo=ethereum&logoColor=white)  **Ensure atomic** software distribution and purchase between manufacturer and device 

- ![ECDSA](https://img.shields.io/badge/ECDSA_Signature-34495E?style=flat&logo=lock&logoColor=white)  Verify update request and installation integrity using **ECDSA signature validation**  

- ![Web3](https://img.shields.io/badge/Web3-F16822?style=flat&logo=web3dotjs&logoColor=white)  **Interact with the blockchain using Web3** libraries  

- ![IPFS](https://img.shields.io/badge/IPFS_File-65C2CB?style=flat&logo=ipfs&logoColor=white)  Download **encrypted update files** from IPFS with **distributed storage** support  

- ![AES-256](https://img.shields.io/badge/AES--256-006699?style=flat&logo=databricks&logoColor=white)  **Decrypt update files** using AES-256 symmetric key to retrieve the original file  

- ![CP-ABE](https://img.shields.io/badge/CP--ABE-6C3483?style=flat&logo=academia&logoColor=white)  Decrypt the encrypted symmetric key using CP-ABE with the device’s secret key, **ensuring that decryption is only possible when the key matches the update policy defined by the manufacturer.**

- ![SHA3-256](https://img.shields.io/badge/SHA3--256-117A65?style=flat&logo=datadog&logoColor=white)  **Verify file integrity** by comparing SHA3-256 hash with blockchain values  

- ![WebSocket](https://img.shields.io/badge/WebSocket-008080?style=flat&logo=socketdotio&logoColor=white)  **Detect blockchain events** in real-time for update monitoring  

- ![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logoColor=white)  Device **backend server** built with Flask.  

## Installation
See [install.md](./install.md) for installation and usage instructions.

## Directory Structure
```
Blocker_Device/
├── backend/
│   └── api.py                      # Backend API entry point
├── blockchain/
│   └── registry_address.json       # Blockchain registry address/config
├── client/
│   ├── device_client.py            # Implements the device update process
│   └── keys/
│       ├── device_secret_key_file.bin  # Device CP-ABE private key
│       └── public_key.bin              # Device Manufacturer Public key
├── crypto/
│   ├── cpabe/
│   │   └── cpabe.py                 # CP-ABE (attribute-based encryption) implementation
│   ├── hash/
│   │   └── hash.py                  # SHA3-256 Hash utilities
│   └── symmetric/
│       └── symmetric.py             # AES-256 Symmetric-key encryption utilities
├── ipfs/
│   └── download/
│       └── download.py             # IPFS download logic
├── Dockerfile                      # Root application Docker build config
├── docker-compose.yml              # Service orchestration config
└── requirements.txt                # Python dependencies list
```

## License

This project is licensed under the MIT License. See [LICENSE](./LICENSE) for details.

---

Contributions and questions are always welcome through Issues and Pull Requests.
For detailed contribution guidelines, please refer to the [Contribution Guide](https://github.com/HSU-Blocker/Blocker_Device?tab=contributing-ov-file).

---

Contributions and questions are welcome via Issues and Pull Requests.
For more information about the overall project, visit the [HSU-Blocker GitHub organization](https://github.com/HSU-Blocker).

<p align="left">
  <a href="https://app.fossa.com/projects/git%2Bgithub.com%2FHSU-Blocker%2FBlocker_Device?ref=badge_large">
    <img src="https://app.fossa.com/api/projects/git%2Bgithub.com%2FHSU-Blocker%2FBlocker_Device.svg?type=large" alt="FOSSA Status Large"/>
  </a>
  <a href="https://app.fossa.com/projects/git%2Bgithub.com%2FHSU-Blocker%2FBlocker_Device?ref=badge_shield">
    <img src="https://app.fossa.com/api/projects/git%2Bgithub.com%2FHSU-Blocker%2FBlocker_Device.svg?type=shield" alt="FOSSA Status Shield"/>
  </a>
</p>

> Note: This project uses Flask as a backend framework but does not distribute or use the Flask logo.
