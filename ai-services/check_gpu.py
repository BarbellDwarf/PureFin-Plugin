#!/usr/bin/env python3
"""
GPU Detection Script for PureFin AI Services
Checks if NVIDIA GPU and Docker GPU support is available.
"""

import subprocess
import sys
import json

def check_nvidia_driver():
    """Check if NVIDIA driver is installed."""
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ NVIDIA driver detected")
            # Parse GPU info from nvidia-smi
            for line in result.stdout.split('\n'):
                if 'NVIDIA' in line and ('GeForce' in line or 'RTX' in line or 'GTX' in line or 'Quadro' in line):
                    print(f"  GPU: {line.strip()}")
            return True
        else:
            print("✗ NVIDIA driver not found")
            return False
    except FileNotFoundError:
        print("✗ nvidia-smi not found (NVIDIA driver not installed)")
        return False
    except Exception as e:
        print(f"✗ Error checking NVIDIA driver: {e}")
        return False

def check_docker_gpu():
    """Check if Docker has GPU support."""
    try:
        # Try to run nvidia-smi in a Docker container
        result = subprocess.run([
            'docker', 'run', '--rm', '--gpus', 'all',
            'nvidia/cuda:11.8.0-base-ubuntu22.04',
            'nvidia-smi'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✓ Docker GPU support is working")
            return True
        else:
            print("✗ Docker GPU support not working")
            print(f"  Error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("✗ Docker not found")
        return False
    except Exception as e:
        print(f"✗ Error checking Docker GPU support: {e}")
        return False

def check_services_health():
    """Check if AI services are running and report GPU status."""
    try:
        import requests
        
        services = {
            'Scene Analyzer': 'http://localhost:3002/health',
            'NSFW Detector': 'http://localhost:3001/health',
            'Content Classifier': 'http://localhost:3004/health'
        }
        
        print("\nChecking running services:")
        for name, url in services.items():
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    gpu_status = "GPU" if data.get('gpu_available') else "CPU"
                    print(f"✓ {name}: Running on {gpu_status}")
                else:
                    print(f"✗ {name}: Not healthy")
            except:
                print(f"  {name}: Not running")
        
        return True
    except ImportError:
        print("\n(Install 'requests' package to check running services)")
        return False

def print_recommendations(has_driver, has_docker_gpu):
    """Print recommendations based on GPU availability."""
    print("\n" + "="*60)
    print("RECOMMENDATIONS:")
    print("="*60)
    
    if has_driver and has_docker_gpu:
        print("🎉 GPU acceleration is fully available!")
        print("\nTo use GPU acceleration:")
        print("  docker-compose -f docker-compose.gpu.yml up -d")
        print("\nExpected performance: 5-10x faster than CPU")
    elif has_driver and not has_docker_gpu:
        print("⚠️  NVIDIA GPU detected but Docker GPU support not configured")
        print("\nTo enable GPU support:")
        print("  1. Install NVIDIA Container Toolkit")
        print("     See: GPU_SETUP.md for instructions")
        print("  2. Restart Docker")
        print("  3. Run this script again to verify")
    else:
        print("ℹ️  No GPU detected - will use CPU")
        print("\nTo start services with CPU:")
        print("  docker-compose up -d")
        print("\nNote: CPU performance is adequate but slower than GPU")

def main():
    """Main function."""
    print("PureFin AI Services - GPU Detection")
    print("="*60)
    
    # Check NVIDIA driver
    has_driver = check_nvidia_driver()
    
    # Check Docker GPU support
    has_docker_gpu = False
    if has_driver:
        print("\nChecking Docker GPU support...")
        has_docker_gpu = check_docker_gpu()
    
    # Check running services
    check_services_health()
    
    # Print recommendations
    print_recommendations(has_driver, has_docker_gpu)
    
    # Exit code
    if has_driver and has_docker_gpu:
        sys.exit(0)  # GPU fully available
    elif has_driver:
        sys.exit(2)  # GPU available but Docker not configured
    else:
        sys.exit(1)  # No GPU

if __name__ == "__main__":
    main()
