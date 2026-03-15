import json
from typing import Any, Dict

def generate_xray_config(server: Dict[str, Any], local_port: int = 1080) -> Dict[str, Any]:
    """
    Parselenmiş sunucu bilgisini Xray JSON config formatına çevirir.
    Eksiksiz (Full) JSON yapısı oluşturur.
    """
    protocol = server.get("protocol", "vless")
    
    # Outbound settings based on protocol
    user_settings = {
        "id": server["uuid"],
        "encryption": "none"
    }
    
    # Flow parametresi (sadece Reality/TLS ve TCP/GRPC için anlamlı olabilir)
    if server.get("flow"):
        user_settings["flow"] = server["flow"]

    outbound_settings = {
        "vnext": [{
            "address": server["address"],
            "port": int(server["port"]),
            "users": [user_settings]
        }]
    }

    # Stream Settings (Network & Security)
    stream_settings = {
        "network": server.get("network", "tcp"),
        "security": server.get("security", ""),
    }

    # Network specific settings
    if stream_settings["network"] == "ws":
        stream_settings["wsSettings"] = {
            "path": server.get("path", "/"),
            "headers": {
                "Host": server.get("host", server.get("sni", ""))
            }
        }
    elif stream_settings["network"] == "grpc":
        stream_settings["grpcSettings"] = {
            "serviceName": server.get("serviceName", ""),
            "multiMode": True
        }
    elif stream_settings["network"] == "http":
        stream_settings["httpSettings"] = {
            "path": server.get("path", "/"),
            "host": [server.get("host", server.get("sni", ""))]
        }

    # Security specific settings
    if stream_settings["security"] == "tls":
        stream_settings["tlsSettings"] = {
            "serverName": server.get("sni", ""),
            "allowInsecure": server.get("allowInsecure", "0") == "1",
            "alpn": server.get("alpn", "h2,http/1.1").split(",") if server.get("alpn") else ["h2", "http/1.1"],
            "fingerprint": server.get("fingerprint", "chrome")
        }
    elif stream_settings["security"] == "reality":
        stream_settings["realitySettings"] = {
            "show": False,
            "fingerprint": server.get("fingerprint", "chrome"),
            "serverName": server.get("sni", ""),
            "publicKey": server.get("publicKey", ""),
            "shortId": server.get("shortId", ""),
            "spiderX": server.get("spiderX", "")
        }

    # "Uzun JSON" yapısı için ek katmanlar (Policy, DNS, Log vb.)
    config = {
        "log": {
            "access": "",
            "error": "",
            "loglevel": "none"
        },
        "inbounds": [{
            "port": local_port,
            "listen": "127.0.0.1",
            "protocol": "socks",
            "sniffing": {
                "enabled": True,
                "destOverride": ["http", "tls"]
            },
            "settings": {
                "auth": "noauth",
                "udp": True,
                "ip": "127.0.0.1"
            }
        }],
        "outbounds": [
            {
                "tag": "proxy",
                "protocol": protocol,
                "settings": outbound_settings,
                "streamSettings": stream_settings,
                "mux": {
                    "enabled": False,
                    "concurrency": -1
                }
            },
            {
                "tag": "direct",
                "protocol": "freedom",
                "settings": {}
            },
            {
                "tag": "block",
                "protocol": "blackhole",
                "settings": {}
            }
        ],
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [
                {
                    "type": "field",
                    "inboundTag": ["api"],
                    "outboundTag": "api"
                },
                {
                    "type": "field",
                    "outboundTag": "proxy",
                    "port": "53"
                }
            ]
        },
        "policy": {
            "levels": {
                "0": {
                    "statsUserUplink": True,
                    "statsUserDownlink": True
                }
            },
            "system": {
                "statsInboundUplink": True,
                "statsInboundDownlink": True
            }
        }
    }

    return config

if __name__ == "__main__":
    # Test örneği
    sample_server = {
        "protocol": "vless",
        "address": "example.com",
        "port": 443,
        "uuid": "00000000-0000-0000-0000-000000000000",
        "network": "tcp",
        "security": "reality",
        "sni": "google.com",
        "fingerprint": "chrome",
        "publicKey": "pbk_here",
        "shortId": "sid_here",
        "spiderX": "/path"
    }
    print(json.dumps(generate_xray_config(sample_server), indent=2))
