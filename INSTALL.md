# Installation Guide
 (Blocker_Device)

This document is based on the **[Blocker_Device](https://github.com/HSU-Blocker/Blocker_Device)** repository  
and provides installation instructions for running actual update processes on IoT devices  
(e.g., autonomous vehicle prototypes, Raspberry Pi, or other IoT hardware).  

## Prerequisites
- **Docker** and **Docker Compose** installed  
- **Git** installed  

## 1. Clone the Repository

```sh
git clone https://github.com/HSU-Blocker/Blocker_Device.git
cd Blocker_Device
```

## 2. Configure .env

Create a .env file in the root directory of the project with the following content:

```
# Environment
FLASK_ENV=development

# Blockchain Configuration
WEB3_PROVIDER={YOUR_WEB3_PROVIDER}
WEB3_WS_PROVIDER=ws://{YOUR_WEB3_WS_PROVIDER}

# Use one of the default development accounts provided by Ganache
PRIVATE_KEY={YOUR_PRIVATE_KEY}
ACCOUNT_ADDRESS={YOUR_ACCOUNT_ADDRESS}
CONTRACT_ADDRESS={YOUR_CONTRACT_ADDRESS}
CONTRACT_ABI_PATH={YOUR_CONTRACT_ABI_PATH}

# IPFS Configuration
IPFS_API={YOUR_IPFS_API}  # For ipfshttpclient
IPFS_GATEWAY=h{YOUR_IPFS_GATEWAY}  # For HTTP downloads

# Ports
DEVICE_API_PORT={YOUR_DEVICE_API_PORT}
MANUFACTURER_API_PORT={YOUR_MANUFACTURER_API_PORT}

# IoT Device Example Settings
OWNER_ADDRESS={YOUR_OWNER_ADDRESS}
OWNER_PRIVATE_KEY={YOUR_OWNER_PRIVATE_KEY}
PUBLIC_KEY={YOUR_BLOCKCHAIN_PUBLIC_KEY}

# Manufacturer API URL
MANUFACTURER_API_URL={YOUR_MANUFACTURER_API_URL}
```

## 3. Docker Setup

This project is based on a **Python 3.10-slim (arm64)** Docker image,  
which provides the runtime environment for IoT device execution on Ubuntu.

### Build and run the container
Use the following command to build the Docker image and start the container in the background:

```bash
docker-compose up --build -d
```

## Notes

This installation process assumes execution directly on the IoT device.

While tested on an autonomous vehicle prototype, the same process can also be applied
to other IoT devices (e.g., Raspberry Pi).

---

If you encounter any issues, please report them via [Issues](https://github.com/HSU-Blocker/Blocker_Device/issues).
