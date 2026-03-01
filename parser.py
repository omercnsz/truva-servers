"""
parser.py – Toplanan vless:// / reality:// URI'larını ayrıştırarak
standart bir JSON yapısına (servers.json) dönüştürür.

URI formatı (genel):
  vless://<uuid>@<host>:<port>?<params>#<remark>
"""

import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "servers.json"


def _safe_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def parse_vless_uri(uri: str) -> Optional[Dict[str, Any]]:
    """
    Tek bir vless:// veya reality:// URI'sını sözlük yapısına dönüştürür.
    Geçersizse None döndürür.
    """
    try:
        uri = uri.strip()
        if not uri:
            return None

        # Boşluk / kontrol karakterlerini temizle (bazı kaynaklarda oluyor)
        uri = uri.replace(" ", "%20").replace("\t", "").replace("\r", "")

        # reality:// → vless:// olarak normalize et, protocol alanında sakla
        original_scheme = "reality" if uri.startswith("reality://") else "vless"
        normalized = uri
        if original_scheme == "reality":
            normalized = "vless" + uri[len("reality"):]

        parsed = urlparse(normalized)

        if not parsed.hostname or not parsed.port:
            return None

        uuid = parsed.username or ""
        if not re.match(r"^[0-9a-fA-F\-]{36}$", uuid) and len(uuid) < 5:
            return None  # geçersiz UUID

        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        # Remark: URL-encoded olmayabilir, hata verirse ham halini kullan
        try:
            remark = unquote(parsed.fragment) if parsed.fragment else ""
        except Exception:
            remark = parsed.fragment or ""

        # Fingerprint hash – benzersiz sunucu kimliği
        fingerprint_src = f"{parsed.hostname}:{parsed.port}:{uuid}"
        fingerprint = hashlib.sha256(fingerprint_src.encode()).hexdigest()[:12]

        server: Dict[str, Any] = {
            "id": fingerprint,
            "protocol": original_scheme,
            "address": parsed.hostname,
            "port": parsed.port,
            "uuid": uuid,
            "remark": remark,
            # ─── TLS / Reality parametreleri ───
            "network": params.get("type", "tcp"),
            "security": params.get("security", ""),
            "sni": params.get("sni", ""),
            "fingerprint": params.get("fp", ""),
            "publicKey": params.get("pbk", ""),
            "shortId": params.get("sid", ""),
            "spiderX": params.get("spx", ""),
            "flow": params.get("flow", ""),
            # ─── WS / gRPC / HTTP ekstra ───
            "path": params.get("path", ""),
            "host": params.get("host", ""),
            "serviceName": params.get("serviceName", ""),
            "alpn": params.get("alpn", ""),
            "allowInsecure": params.get("allowInsecure", "0"),
            # ─── Meta ───
            "raw": uri,
        }
        return server

    except Exception:
        # Beklenmeyen her türlü format hatası sessizce None döndürür
        return None


def deduplicate(servers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """id alanına göre tekrar eden sunucuları kaldırır."""
    seen = set()
    unique = []
    for s in servers:
        if s["id"] not in seen:
            seen.add(s["id"])
            unique.append(s)
    return unique


def build_servers_json(raw_links: List[str]) -> Dict[str, Any]:
    """
    Ham URI listesinden temizlenmiş servers.json yapısını üretir.
    """
    parsed = []
    failed = 0
    for link in raw_links:
        result = parse_vless_uri(link)
        if result:
            parsed.append(result)
        else:
            failed += 1

    unique = deduplicate(parsed)

    # Protokole göre ayır
    reality_servers = [s for s in unique if s["security"] == "reality" or s["protocol"] == "reality"]
    vless_tls = [s for s in unique if s not in reality_servers and s["security"] == "tls"]
    vless_other = [s for s in unique if s not in reality_servers and s not in vless_tls]

    output = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total": len(unique),
            "reality_count": len(reality_servers),
            "vless_tls_count": len(vless_tls),
            "vless_other_count": len(vless_other),
            "parse_failures": failed,
        },
        "servers": {
            "reality": reality_servers,
            "vless_tls": vless_tls,
            "vless_other": vless_other,
        },
    }
    return output


def save_json(data: Dict[str, Any], path: Path = OUTPUT_FILE) -> Path:
    """JSON verisini dosyaya yazar."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


# ─── Doğrudan çalıştırma ───
if __name__ == "__main__":
    from scraper import collect_all

    links = collect_all()
    data = build_servers_json(links)
    out = save_json(data)

    meta = data["metadata"]
    print(f"\n✅ servers.json oluşturuldu → {out}")
    print(f"   Toplam: {meta['total']}  |  Reality: {meta['reality_count']}  "
          f"|  VLESS-TLS: {meta['vless_tls_count']}  |  Diğer: {meta['vless_other_count']}")
    print(f"   Ayrıştırma hataları: {meta['parse_failures']}")
