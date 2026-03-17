import json
import logging
import os
from datetime import datetime
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
    logger.info("═══ Havuz yönetimi başladı (Dual-Type: Genel + Oyun) ═══")
    
    # 1. Mevcut sunucuları test et
    existing = load_existing_servers()
    working_servers = [] # Sadece TCP (veya hem TCP hem UDP) çalışan her şey
    
    logger.info(f"Mevcut {len(existing)} sunucu kontrol ediliyor...")
    for s in existing:
        res = test_server_with_xray(s, xray_path=XRAY_PATH)
        if res["tcp"]:
            s["udp_supported"] = res["udp"] # Flag olarak sakla
            working_servers.append(s)
            status = "UDP+TCP" if res["udp"] else "Sadece TCP"
            logger.info(f"  [{status}] {s['id']} - {s['remark']}")
        else:
            logger.info(f"  [ÖLÜ] {s['id']} - {s['remark']}")
        
        if len(working_servers) >= POOL_SIZE * 3: # Havuz sınırını geniş tutalım
            break

    # 2. Eğer havuz dolmadıysa yeni link kazı
    if len(working_servers) < POOL_SIZE * 2:
        logger.info("Havuz yetersiz, yeni kaynaklar taranıyor...")
        raw_links = collect_all()
        seen_ids = {s["id"] for s in working_servers}
        
        for link in raw_links:
            parsed = parse_vless_uri(link)
            if not parsed or parsed["id"] in seen_ids:
                continue
            
            # Gaming için uygunsuz protokolleri sadece UDP flag'i için not ediyoruz, 
            # ancak TCP çalışıyorsa "Genel" havuza alıyoruz.
            logger.info(f"Yeni sunucu test ediliyor: {parsed['id']}...")
            res = test_server_with_xray(parsed, xray_path=XRAY_PATH)
            
            if res["tcp"]:
                parsed["udp_supported"] = res["udp"]
                working_servers.append(parsed)
                seen_ids.add(parsed["id"])
                status = "UDP+TCP" if res["udp"] else "Sadece TCP"
                logger.info(f"  [KAYDEDİLDİ - {status}] {parsed['remark']}")
            
            if len(working_servers) >= POOL_SIZE * 3:
                break

    # 3. KATEGORİZASYON
    # Oyun sunucuları: UDP desteği olanlar
    gaming_pool = [s for s in working_servers if s.get("udp_supported")]
    # Genel sunucular: UDP'si olmayan ama TCP'si çalışanlar
    general_pool = [s for s in working_servers if not s.get("udp_supported")]

    # Her kategoriden en iyileri (veya ilk bulunanları) seç
    final_gaming = gaming_pool[:POOL_SIZE]
    final_general = general_pool[:POOL_SIZE]

    # Teknik kategorilere ayırma (Reality, TLS vb.) - JSON yapısını korumak için
    def split_by_tech(pool):
        reality = [s for s in pool if s.get("security") == "reality" or s.get("protocol") == "reality"]
        vless_tls = [s for s in pool if s not in reality and s.get("security") == "tls"]
        vless_other = [s for s in pool if s not in reality and s not in vless_tls]
        return reality, vless_tls, vless_other

    g_reality, g_tls, g_other = split_by_tech(final_gaming)
    w_reality, w_tls, w_other = split_by_tech(final_general)

    output_data = {
        "metadata": {
            "total_working": len(working_servers),
            "gaming_count": len(final_gaming),
            "general_count": len(final_general),
            "last_check": str(datetime.now())
        },
        "gaming": {
            "reality": g_reality,
            "vless_tls": g_tls,
            "vless_other": g_other,
        },
        "general": {
            "reality": w_reality,
            "vless_tls": w_tls,
            "vless_other": w_other,
        }
    }
    
    save_json(output_data)
    logger.info(f"Havuz güncellendi (Oyun: {len(final_gaming)}, Genel: {len(final_general)})")
    logger.info("═══ Havuz yönetimi tamamlandı ═══")

if __name__ == "__main__":
    # Xray binary'sinin adını OS'a göre ayarla
    if os.name == 'nt':
        XRAY_PATH = "xray.exe"
    else:
        XRAY_PATH = "./xray"  # Linux (GitHub Actions) için ./xray olmalı
    
    run_pool_management()
