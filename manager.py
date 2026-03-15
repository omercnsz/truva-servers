import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any

from scraper import collect_all
from parser import parse_vless_uri, save_json, OUTPUT_FILE
from tester import test_server_with_xray

# Konfigürasyon
POOL_SIZE = 20
XRAY_PATH = "xray" # GitHub Actions'da 'xray' olacak. Lokal için .exe gerekebilir.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

def load_existing_servers() -> List[Dict[str, Any]]:
    """Mevcut servers.json dosyasını yükler."""
    if not OUTPUT_FILE.exists():
        return []
    try:
        data = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
        # servers.json yapısı { "servers": { "reality": [], "vless_tls": [], ... } }
        # Tüm listeleri birleştirip döndürelim
        all_servers = []
        for category in data.get("servers", {}).values():
            all_servers.extend(category)
        return all_servers
    except Exception as e:
        logger.error(f"Eski sunucular yüklenemedi: {e}")
        return []

def run_pool_management():
    logger.info("═══ Havuz yönetimi başladı ═══")
    
    # 1. Mevcut sunucuları test et (Health Check)
    existing = load_existing_servers()
    healthy_servers = []
    
    logger.info(f"Mevcut {len(existing)} sunucu kontrol ediliyor...")
    for s in existing:
        if test_server_with_xray(s, xray_path=XRAY_PATH):
            s["udp_supported"] = True
            healthy_servers.append(s)
            logger.info(f"  [SAĞLIKLI] {s['id']} - {s['remark']}")
        else:
            logger.info(f"  [ÖLÜ/YAVAŞ] {s['id']} - {s['remark']}")
        
        if len(healthy_servers) >= POOL_SIZE:
            break

    logger.info(f"Sağlıklı kalan: {len(healthy_servers)}/{POOL_SIZE}")

    # 2. Eğer havuz dolmadıysa yeni link kazı
    if len(healthy_servers) < POOL_SIZE:
        logger.info("Havuz eksik, yeni kaynaklar taranıyor...")
        raw_links = collect_all()
        
        # Daha önce test ettiklerimizi (healthy ve ölüler dahil) pas geçmek için kimlikleri alalım
        seen_ids = {s["id"] for s in existing}
        
        for link in raw_links:
            parsed = parse_vless_uri(link)
            if not parsed or parsed["id"] in seen_ids:
                continue
            
            logger.info(f"Yeni sunucu test ediliyor: {parsed['id']}...")
            if test_server_with_xray(parsed, xray_path=XRAY_PATH):
                parsed["udp_supported"] = True
                healthy_servers.append(parsed)
                seen_ids.add(parsed["id"])
                logger.info(f"  [KAYDEDİLDİ] {parsed['remark']}")
            
            if len(healthy_servers) >= POOL_SIZE:
                logger.info("Havuz 20'ye ulaştı, tarama durduruldu.")
                break

    # 3. Sonuçları kategorize et ve kaydet
    reality_servers = [s for s in healthy_servers if s.get("security") == "reality" or s.get("protocol") == "reality"]
    vless_tls = [s for s in healthy_servers if s not in reality_servers and s.get("security") == "tls"]
    vless_other = [s for s in healthy_servers if s not in reality_servers and s not in vless_tls]

    output_data = {
        "metadata": {
            "total": len(healthy_servers),
            "reality_count": len(reality_servers),
            "vless_tls_count": len(vless_tls),
            "vless_other_count": len(vless_other),
            "last_check": Path(__file__).stat().st_mtime # Veya datetime.now()
        },
        "servers": {
            "reality": reality_servers,
            "vless_tls": vless_tls,
            "vless_other": vless_other,
        }
    }
    
    save_json(output_data)
    logger.info(f"Havuz güncellendi ve kaydedildi: {OUTPUT_FILE}")
    logger.info("═══ Havuz yönetimi tamamlandı ═══")

if __name__ == "__main__":
    # Xray binary'sinin adını OS'a göre ayarla
    if os.name == 'nt':
        XRAY_PATH = "xray.exe"
    else:
        XRAY_PATH = "./xray"  # Linux (GitHub Actions) için ./xray olmalı
    
    run_pool_management()
