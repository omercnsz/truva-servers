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
    logger.info("═══ Havuz yönetimi başladı (Oyun Odaklı: Reality Öncelikli) ═══")
    
    # 1. Mevcut sunucuları test et (Health Check)
    existing = load_existing_servers()
    all_healthy = []
    
    logger.info(f"Mevcut {len(existing)} sunucu kontrol ediliyor...")
    for s in existing:
        # Gaming için uygunsuz protokolleri (WS gibi) deprioritize et veya elendiklerinden emin ol
        # Ancak zaten havuza girmişse sağlıklıdır.
        if test_server_with_xray(s, xray_path=XRAY_PATH):
            s["udp_supported"] = True
            all_healthy.append(s)
            logger.info(f"  [SAĞLIKLI] {s['id']} - {s['remark']}")
        else:
            logger.info(f"  [ÖLÜ/YAVAŞ] {s['id']} - {s['remark']}")
        
        if len(all_healthy) >= POOL_SIZE * 2: # Daha fazla toplayıp sonra içinden en iyileri seçeceğiz
            break

    # 2. Eğer havuz dolmadıysa yeni link kazı
    if len(all_healthy) < POOL_SIZE:
        logger.info("Havuz yetersiz, yeni kaynaklar taranıyor...")
        raw_links = collect_all()
        
        seen_ids = {s["id"] for s in all_healthy}
        
        for link in raw_links:
            parsed = parse_vless_uri(link)
            if not parsed or parsed["id"] in seen_ids:
                continue
            
            # KRİTİK FİLTRE: WS (WebSocket) ve Cloudflare tabanlı linkleri oyun için uygun olmadığından eliyoruz
            network = parsed.get("network", "tcp").lower()
            remark = parsed.get("remark", "").lower()
            if network == "ws" or "cloudflare" in remark or "cdc" in remark:
                logger.debug(f"  [ATLANDI - GAMING] {parsed['remark']} (WS/Cloudflare)")
                continue

            logger.info(f"Yeni sunucu test ediliyor: {parsed['id']}...")
            if test_server_with_xray(parsed, xray_path=XRAY_PATH):
                parsed["udp_supported"] = True
                all_healthy.append(parsed)
                seen_ids.add(parsed["id"])
                logger.info(f"  [KAYDEDİLDİ] {parsed['remark']}")
            
            if len(all_healthy) >= POOL_SIZE * 2:
                break

    # 3. SIRALAMA VE SEÇİM: Reality protokollerini en başa al, sonra diğerlerini ekle
    reality_pool = [s for s in all_healthy if s.get("security") == "reality" or s.get("protocol") == "reality"]
    others_pool = [s for s in all_healthy if s not in reality_pool]
    
    # Yeni havuzu oluştur: Önce Reality, sonra kalanlar (toplam POOL_SIZE kadar)
    final_pool = (reality_pool + others_pool)[:POOL_SIZE]

    reality_final = [s for s in final_pool if s.get("security") == "reality" or s.get("protocol") == "reality"]
    vless_tls = [s for s in final_pool if s not in reality_final and s.get("security") == "tls"]
    vless_other = [s for s in final_pool if s not in reality_final and s not in vless_tls]

    output_data = {
        "metadata": {
            "total": len(final_pool),
            "reality_count": len(reality_final),
            "vless_tls_count": len(vless_tls),
            "vless_other_count": len(vless_other),
            "last_check": str(datetime.now())
        },
        "servers": {
            "reality": reality_final,
            "vless_tls": vless_tls,
            "vless_other": vless_other,
        }
    }
    
    save_json(output_data)
    logger.info(f"Havuz güncellendi (Reality: {len(reality_final)}): {OUTPUT_FILE}")
    logger.info("═══ Havuz yönetimi tamamlandı ═══")

if __name__ == "__main__":
    # Xray binary'sinin adını OS'a göre ayarla
    if os.name == 'nt':
        XRAY_PATH = "xray.exe"
    else:
        XRAY_PATH = "./xray"  # Linux (GitHub Actions) için ./xray olmalı
    
    run_pool_management()
