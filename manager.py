import json
import logging
import os
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from scraper import collect_all
from parser import parse_vless_uri, save_json, OUTPUT_FILE
from tester import test_server_with_xray

# Konfigürasyon
POOL_SIZE = 20
MAX_THREADS = 10
XRAY_PATH = "xray" 

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
        all_servers = []
        # Eski yapıda servers anahtarı altındaydı, yeni yapıda gaming/general altında
        if "servers" in data:
            for category in data.get("servers", {}).values():
                all_servers.extend(category)
        else:
            for category in ["gaming", "general"]:
                if category in data:
                    for tech in data[category].values():
                        all_servers.extend(tech)
        return all_servers
    except Exception as e:
        logger.error(f"Eski sunucular yüklenemedi: {e}")
        return []

def test_single_server(server: Dict[str, Any], port: int) -> Optional[Dict[str, Any]]:
    """Tek bir sunucuyu test eder ve başarılıysa döndürür."""
    res = test_server_with_xray(server, xray_path=XRAY_PATH, local_port=port)
    if res["tcp"]:
        server["udp_supported"] = res["udp"]
        return server
    return None

def run_pool_management():
    logger.info(f"═══ Havuz yönetimi başladı (Paralel Test - {MAX_THREADS} Thread) ═══")
    
    existing = load_existing_servers()
    working_servers = []
    
    # 1. Mevcut sunucuları paralel test et
    if existing:
        logger.info(f"Mevcut {len(existing)} sunucu kontrol ediliyor...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            # Portları 10000'den başlatarak çakışmayı önle
            future_to_server = {
                executor.submit(test_single_server, s, 10000 + i % MAX_THREADS): s 
                for i, s in enumerate(existing)
            }
            for future in concurrent.futures.as_completed(future_to_server):
                result = future.result()
                if result:
                    working_servers.append(result)
                    status = "UDP+TCP" if result["udp_supported"] else "Sadece TCP"
                    logger.info(f"  [{status}] {result['id']} - {result['remark']}")
                
                if len(working_servers) >= POOL_SIZE * 4:
                    break

    # 2. Eğer havuz dolmadıysa yeni linkleri paralel kazı ve test et
    if len(working_servers) < POOL_SIZE * 2:
        logger.info("Havuz yetersiz, yeni kaynaklar taranıyor...")
        raw_links = collect_all()
        seen_ids = {s["id"] for s in working_servers}
        
        candidates = []
        for link in raw_links:
            parsed = parse_vless_uri(link)
            if parsed and parsed["id"] not in seen_ids:
                candidates.append(parsed)
                seen_ids.add(parsed["id"])
            if len(candidates) >= 150: # Çok fazla link test edip vakit kaybetmeyelim
                break

        logger.info(f"{len(candidates)} yeni aday test ediliyor...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            future_to_new = {
                executor.submit(test_single_server, s, 11000 + i % MAX_THREADS): s 
                for i, s in enumerate(candidates)
            }
            for future in concurrent.futures.as_completed(future_to_new):
                result = future.result()
                if result:
                    working_servers.append(result)
                    status = "UDP+TCP" if result["udp_supported"] else "Sadece TCP"
                    logger.info(f"  [KAYDEDİLDİ - {status}] {result['remark']}")
                
                if len(working_servers) >= POOL_SIZE * 4:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

    # 3. KATEGORİZASYON VE KAYIT
    gaming_pool = [s for s in working_servers if s.get("udp_supported")]
    general_pool = [s for s in working_servers if not s.get("udp_supported")]

    final_gaming = gaming_pool[:POOL_SIZE]
    final_general = general_pool[:POOL_SIZE]

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
        "servers": {
            # Uygulamanın beklediği ana anahtar (Geriye dönük uyumluluk)
            # Burada oyun sunucularını ve genel sunucuları öncelik sırasına göre birleştiriyoruz
            "reality": g_reality + w_reality,
            "vless_tls": g_tls + w_tls,
            "vless_other": g_other + w_other,
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
    if os.name == 'nt':
        XRAY_PATH = "xray.exe"
    else:
        XRAY_PATH = "./xray"
    
    run_pool_management()
