"""
main.py – Ana giriş noktası. Scraper + Parser'ı birlikte çalıştırır.
GitHub Actions veya elle çalıştırma için kullanılır.
"""

import sys
import logging
from pathlib import Path

from scraper import collect_all
from parser import build_servers_json, save_json, OUTPUT_FILE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    logger.info("═══ Veri toplama başladı ═══")

    # 1. Linkleri topla
    raw_links = collect_all()
    if not raw_links:
        logger.error("Hiç link toplanamadı – çıkılıyor.")
        return 1

    # 2. Ayrıştır ve JSON oluştur
    data = build_servers_json(raw_links)
    meta = data["metadata"]
    logger.info(
        "Ayrıştırma bitti → Toplam: %d  |  Reality: %d  |  VLESS-TLS: %d  |  Diğer: %d  |  Hata: %d",
        meta["total"],
        meta["reality_count"],
        meta["vless_tls_count"],
        meta["vless_other_count"],
        meta["parse_failures"],
    )

    # 3. Dosyaya yaz
    out_path = save_json(data)
    logger.info("JSON yazıldı → %s", out_path)

    # 4. Ayrıca output/index.html oluştur (GitHub Pages için)
    _generate_index_html(out_path.parent)

    logger.info("═══ Tamamlandı ═══")
    return 0


def _generate_index_html(output_dir: Path):
    """GitHub Pages'ın kök sayfası – servers.json'a yönlendirir."""
    html = """\
<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>V2Ray Sunucu Listesi API</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 700px; margin: 4rem auto; padding: 0 1rem; color: #e0e0e0; background: #1a1a2e; }
    h1 { color: #00d2ff; }
    a { color: #00d2ff; }
    code { background: #16213e; padding: 2px 6px; border-radius: 4px; }
    .card { background: #16213e; border-radius: 8px; padding: 1.5rem; margin: 1rem 0; }
    .badge { display: inline-block; background: #0f3460; padding: 3px 10px; border-radius: 12px; font-size: 0.85rem; margin: 2px; }
  </style>
</head>
<body>
  <h1>&#x1F310; V2Ray Sunucu Listesi</h1>
  <div class="card">
    <p><strong>API Endpoint:</strong></p>
    <p><code><a href="servers.json">servers.json</a></code></p>
    <p>Bu dosya her <strong>1 saatte</strong> bir otomatik olarak güncellenir.</p>
  </div>
  <div class="card">
    <h3>Kullanım</h3>
    <p>JSON dosyasını doğrudan çekebilirsiniz:</p>
    <code>fetch("https://&lt;username&gt;.github.io/&lt;repo&gt;/servers.json")</code>
  </div>
  <div class="card">
    <h3>Yapı</h3>
    <p><span class="badge">metadata</span> <span class="badge">servers.reality</span> <span class="badge">servers.vless_tls</span> <span class="badge">servers.vless_other</span></p>
  </div>
  <p style="font-size:0.8rem;color:#666;">Son güncelleme otomatik olarak GitHub Actions tarafından yapılmaktadır.</p>
</body>
</html>
"""
    (output_dir / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
