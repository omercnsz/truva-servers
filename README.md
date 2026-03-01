# 🌐 V2Ray Server Collector

Açık kaynaklardan **vless://** ve **reality://** yapılandırma linklerini otomatik olarak toplayan, ayrıştıran ve GitHub Pages üzerinden JSON API olarak sunan otonom sistem.

## 📁 Proje Yapısı

```
├── scraper.py                  # Kaynaklardan link toplama
├── parser.py                   # URI ayrıştırma + JSON üretimi
├── main.py                     # Ana giriş noktası
├── requirements.txt            # Python bağımlılıkları
├── .github/
│   └── workflows/
│       └── update-servers.yml  # GitHub Actions (6 saatte bir)
└── output/
    ├── servers.json            # Üretilen API verisi
    └── index.html              # GitHub Pages ana sayfası
```

## 🚀 Hızlı Başlangıç

### Yerel Çalıştırma

```bash
pip install -r requirements.txt
python main.py
```

Çıktı `output/servers.json` dosyasına yazılır.

### GitHub'a Yükleme

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<KULLANICI>/<REPO>.git
git push -u origin main
```

### GitHub Pages Kurulumu

1. GitHub reposunda **Settings → Pages** bölümüne gidin
2. **Source** olarak **GitHub Actions** seçin
3. İlk workflow çalıştıktan sonra API şu adreste yayınlanır:
   ```
   https://<KULLANICI>.github.io/<REPO>/servers.json
   ```

## ⏰ Otomasyon

GitHub Actions workflow'u otomatik olarak:
- Her **1 saatte** bir çalışır (`0 */1 * * *`)
- `main` branch'e push yapıldığında çalışır
- Actions sekmesinden **elle tetiklenebilir**

## 📊 JSON Yapısı (servers.json)

```json
{
  "metadata": {
    "generated_at": "2026-03-01T12:00:00+00:00",
    "total": 542,
    "reality_count": 180,
    "vless_tls_count": 230,
    "vless_other_count": 132,
    "parse_failures": 15
  },
  "servers": {
    "reality": [ { "id": "...", "address": "...", "port": 443, ... } ],
    "vless_tls": [ ... ],
    "vless_other": [ ... ]
  }
}
```

Her sunucu nesnesi şu alanları içerir:

| Alan | Açıklama |
|------|----------|
| `id` | Benzersiz parmak izi (SHA-256, 12 karakter) |
| `protocol` | `vless` veya `reality` |
| `address` | Sunucu IP/hostname |
| `port` | Bağlantı noktası |
| `uuid` | Kullanıcı kimliği |
| `network` | `tcp`, `ws`, `grpc`, `http` |
| `security` | `reality`, `tls`, `none` |
| `sni` | TLS Server Name Indication |
| `publicKey` | Reality public key |
| `shortId` | Reality short ID |
| `flow` | Akış kontrol yöntemi |
| `remark` | İsteğe bağlı açıklama |

## ➕ Yeni Kaynak Ekleme

[scraper.py](scraper.py) dosyasındaki `SOURCES` listesine yeni bir giriş ekleyin:

```python
{
    "name": "Açıklayıcı isim",
    "type": "github_raw",   # veya "telegram"
    "url": "https://...",
},
```

## 📄 Lisans

MIT
