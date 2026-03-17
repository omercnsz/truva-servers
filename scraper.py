"""
scraper.py – Açık kaynaklardan vless:// ve reality:// yapılandırma linklerini toplar.

Desteklenen kaynaklar:
  • GitHub repoları (raw dosyalar)
  • Telegram kanal web önizlemeleri (t.me/s/ üzerinden)
  • Düz metin abonelik URL'leri

Yeni kaynak eklemek için SOURCES listesine ekleme yapmanız yeterlidir.
"""

import re
import base64
import requests
import logging
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# KAYNAK LİSTESİ – istediğiniz kadar ekleyebilirsiniz
# ──────────────────────────────────────────────
SOURCES: List[dict] = [
    # ── sevcator/5ubscrpt10n (aktif, saatlik güncelleme, 111 yıldız) ──
    {
        "name": "sevcator/5ubscrpt10n – VLESS",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/sevcator/5ubscrpt10n/main/protocols/vl.txt",
    },
    # ── MahanKenway/Freedom-V2Ray (aktif, 2 saatte bir güncelleme) ──
    {
        "name": "MahanKenway/Freedom-V2Ray – VLESS",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/configs/vless.txt",
    },
    {
        "name": "MahanKenway/Freedom-V2Ray – Mix",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/configs/mix.txt",
    },
    # ── Epodonios/v2ray-configs ──
    {
        "name": "Epodonios/v2ray-configs – All",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_Sub.txt",
    },
    # ── Delta-Kronecker/V2ray-Config – vless ──
    {
        "name": "Delta-Kronecker/V2ray-Config – VLESS",
        "type": "github_raw",
        "url": "https://github.com/Delta-Kronecker/V2ray-Config/raw/refs/heads/main/config/protocols/vless.txt",
    },
    {
        "name": "Delta-Kronecker/V2ray-Config – All",
        "type": "github_raw",
        "url": "https://github.com/Delta-Kronecker/V2ray-Config/raw/refs/heads/main/config/all_configs.txt",
    },
    # ── sakha1370/OpenRay ──
    {
        "name": "sakha1370/OpenRay – valid proxies",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/sakha1370/OpenRay/refs/heads/main/output/all_valid_proxies.txt",
    },
    # ── V2RayRoot/V2RayConfig ──
    {
        "name": "V2RayRoot/V2RayConfig – VLESS",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/V2RayRoot/V2RayConfig/refs/heads/main/Config/vless.txt",
    },
    # ── Kolandone/v2raycollector ──
    {
        "name": "Kolandone/v2raycollector – VLESS",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/Kolandone/v2raycollector/refs/heads/main/vless.txt",
    },
    # ── youfoundamin/V2rayCollector ──
    {
        "name": "youfoundamin/V2rayCollector – mixed",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/youfoundamin/V2rayCollector/main/mixed_iran.txt",
    },
    # ── barry-far/V2ray-config (yeni repo) ──
    {
        "name": "barry-far/V2ray-config – VLESS",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/vless.txt",
    },
    {
        "name": "barry-far/V2ray-config – All",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/barry-far/V2ray-config/main/All_Configs_Sub.txt",
    },
    # ── MrMohebi/xray-proxy-grabber-telegram ──
    {
        "name": "MrMohebi/xray-proxy-grabber – all",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/MrMohebi/xray-proxy-grabber-telegram/master/collected-proxies/row-url/all.txt",
    },
    # ── Surfboardv2ray/TGParse ──
    {
        "name": "Surfboardv2ray/TGParse – vless",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/splitted/vless",
    },
    {
        "name": "Surfboardv2ray/TGParse – mixed",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/splitted/mixed",
    },
    # ── itsyebekhe/PSG ──
    {
        "name": "itsyebekhe/PSG – mix base64",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/itsyebekhe/PSG/main/subscriptions/xray/base64/mix",
    },
    # ── roosterkid/openproxylist ──
    {
        "name": "roosterkid/openproxylist – V2RAY",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/roosterkid/openproxylist/main/V2RAY_RAW.txt",
    },
    # ── jafarm83/ConfigV2Ray ──
    {
        "name": "jafarm83/ConfigV2Ray",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/jafarm83/ConfigV2Ray/main/jafar.txt",
    },
    # ── F0rc3Run – vless ──
    {
        "name": "F0rc3Run – vless",
        "type": "github_raw",
        "url": "https://raw.githubusercontent.com/F0rc3Run/F0rc3Run/main/splitted-by-protocol/vless.txt",
    },
    # ── Telegram Kanal Önizlemeleri ──
    {
        "name": "Telegram: vaboron",
        "type": "telegram",
        "url": "https://t.me/s/vaboron",
    },
    {
        "name": "Telegram: RealityV2ray",
        "type": "telegram",
        "url": "https://t.me/s/RealityV2ray",
    },
    {
        "name": "Telegram: VlessConfig",
        "type": "telegram",
        "url": "https://t.me/s/vlessconfig",
    },
]

# vless://, reality://, hysteria2://, tuic:// ile başlayan URI'ları yakalayan regex
LINK_PATTERN = re.compile(r"(?:vless|reality|hysteria2|tuic)://[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+")

# İstek zaman aşımı (saniye)
REQUEST_TIMEOUT = 30


def _try_base64_decode(text: str) -> str:
    """Metin base64 ile kodlanmışsa çözer, değilse olduğu gibi döndürür."""
    stripped = text.strip()
    # Çok kısa veya zaten link içeriyorsa çözme
    if len(stripped) < 20 or "://" in stripped[:80]:
        return text
    try:
        decoded = base64.b64decode(stripped, validate=True).decode("utf-8", errors="ignore")
        if "://" in decoded:
            return decoded
    except Exception:
        pass
    return text


def fetch_links_from_url(url: str) -> List[str]:
    """Tek bir URL'den vless/reality linklerini çeker."""
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        resp.raise_for_status()
        body = _try_base64_decode(resp.text)
        return LINK_PATTERN.findall(body)
    except requests.RequestException as exc:
        logger.warning("İstek başarısız: %s → %s", url, exc)
        return []


def collect_all() -> List[str]:
    """Tüm kaynaklardan linkleri toplar ve tekrarsız liste döndürür."""
    all_links: List[str] = []
    for source in SOURCES:
        name = source["name"]
        url = source["url"]
        logger.info("Taranıyor: %s", name)
        links = fetch_links_from_url(url)
        logger.info("  → %d link bulundu", len(links))
        all_links.extend(links)

    unique = list(dict.fromkeys(all_links))  # sırayı koruyarak tekrarları siler
    logger.info("Toplam benzersiz link: %d", len(unique))
    return unique


if __name__ == "__main__":
    results = collect_all()
    for link in results[:5]:
        print(link)
    print(f"... toplam {len(results)} link")
