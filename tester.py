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
) -> bool:
    """
    Sunucuyu Xray üzerinden çalıştırıp UDP testi (8.8.8.8:53) yapar.
    """
    config = generate_xray_config(server, local_port=local_port)
    config_file = f"temp_config_{server['id']}.json"
    
    try:
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Xray'i başlat
        # Windows'ta .exe ekleme ihtimalini düşün (shell=False daha güvenli)
        cmd = [xray_path, "run", "-c", config_file]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # Xray'in hazır olması için bekle
        time.sleep(2.5)
        
        is_healthy = False
        try:
            # SOCKS5 üzerinden UDP testi
            socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", local_port)
            s = socks.socksocket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(timeout)
            
            # DNS sorgu paketi (google.com A kaydı)
            dns_query = (
                b'\xaa\xaa\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00'
                b'\x06google\x03com\x00\x00\x01\x00\x01'
            )
            
            s.sendto(dns_query, ("8.8.8.8", 53))
            data, addr = s.recvfrom(4096)
            
            if data and len(data) > 0:
                is_healthy = True
                
        except Exception as e:
            logger.debug(f"UDP testi başarısız ({server['id']}): {e}")
            is_healthy = False
        finally:
            s.close()
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                
        return is_healthy
        
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
