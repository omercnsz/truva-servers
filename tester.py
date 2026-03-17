import subprocess
import socket
import time
import json
import os
import logging
from typing import Any, Dict, Optional
import socks

from config_generator import generate_xray_config

logger = logging.getLogger(__name__)

def test_server_with_xray(
    server: Dict[str, Any], 
    xray_path: str = "xray", 
    local_port: int = 1080,
    timeout: float = 5.0
) -> Dict[str, bool]:
    """
    Sunucuyu Xray üzerinden çalıştırıp hem TCP (HTTP) hem de UDP (DNS) testi yapar.
    Döndürür: {"tcp": bool, "udp": bool}
    """
    config = generate_xray_config(server, local_port=local_port)
    config_file = f"temp_config_{server['id']}.json"
    results = {"tcp": False, "udp": False}
    
    try:
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Xray'i başlat
        process = subprocess.Popen(
            [xray_path, "run", "-c", config_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # Xray'in hazır olması için bekle
        time.sleep(2.0)
        
        # 1. TCP TESTİ (HTTP Get - Genel İnternet)
        try:
            proxies = {
                "http": f"socks5h://127.0.0.1:{local_port}",
                "https": f"socks5h://127.0.0.1:{local_port}"
            }
            # requests yerine doğrudan socket ile daha hızlı veya basit bir kontrol yapabiliriz 
            # ancak SOCKS5 üzerinden TCP kontrolü için requests kolaylık sağlar.
            import requests as req
            resp = req.get("http://www.google.com/generate_204", proxies=proxies, timeout=timeout)
            if resp.status_code == 204 or resp.status_code == 200:
                results["tcp"] = True
        except Exception as e:
            logger.debug(f"TCP testi başarısız ({server['id']}): {e}")

        # 2. UDP TESTİ (DNS Query - Oyun)
        try:
            socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", local_port)
            s = socks.socksocket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(timeout)
            dns_query = (
                b'\xaa\xaa\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00'
                b'\x06google\x03com\x00\x00\x01\x00\x01'
            )
            s.sendto(dns_query, ("8.8.8.8", 53))
            data, addr = s.recvfrom(4096)
            if data and len(data) > 0:
                results["udp"] = True
            s.close()
        except Exception as e:
            logger.debug(f"UDP testi başarısız ({server['id']}): {e}")
                
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            
        return results
        
    except Exception as e:
        logger.error(f"Xray başlatma hatası: {e}")
        return results
        
    except Exception as e:
        logger.error(f"Xray başlatma hatası: {e}")
        return False
    finally:
        if os.path.exists(config_file):
            try:
                os.remove(config_file)
            except:
                pass

if __name__ == "__main__":
    # Örnek kullanım (xray binası mevcutsa çalışır)
    logging.basicConfig(level=logging.INFO)
    test_node = {
        "id": "test_node",
        "protocol": "vless",
        "address": "127.0.0.1", # Geçersiz bir adres, false dönmeli
        "port": 443,
        "uuid": "00000000-0000-0000-0000-000000000000"
    }
    # Sonucu yazdır (binary yoksa hata verebilir)
    # print(f"Sıhhat durumu: {test_server_with_xray(test_node)}")
