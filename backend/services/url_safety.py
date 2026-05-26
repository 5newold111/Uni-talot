"""
SSRF 防御: 商品ページから抽出した URL は信頼できない (悪意ある EC ページが
バックエンドを内部サービスに振り向けようとする可能性) ので、
- ホスト解決して private/loopback/link-local IP を排除
- http(s) スキームのみ許可

EC サイトの公開画像 CDN は当然グローバル IP を返すので問題は起きない。
内部 IP に解決される URL は悪意の徴候として弾く。
"""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = ("http", "https")

# RFC 1918 / loopback / link-local / multicast / その他危険な範囲
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),  # loopback
    ipaddress.ip_network("10.0.0.0/8"),  # private
    ipaddress.ip_network("172.16.0.0/12"),  # private
    ipaddress.ip_network("192.168.0.0/16"),  # private
    ipaddress.ip_network("169.254.0.0/16"),  # link-local (AWS metadata 含む)
    ipaddress.ip_network("0.0.0.0/8"),  # this network
    ipaddress.ip_network("100.64.0.0/10"),  # CG-NAT
    ipaddress.ip_network("224.0.0.0/4"),  # multicast
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]


def is_url_safe(url: str) -> tuple[bool, str]:
    """URL が外部公開リソースか検証。

    返値: (安全か, 理由)
    """
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"URL のパース失敗: {e}"

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False, f"許可されないスキーム: {parsed.scheme}"

    if not parsed.hostname:
        return False, "ホスト名がない"

    # ホスト名を IP に解決して private 範囲を弾く
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as e:
        return False, f"DNS 解決失敗: {e}"

    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        for net in _BLOCKED_NETWORKS:
            if ip in net:
                return False, f"内部 IP に解決される ({ip} ∈ {net})"
        if ip.is_reserved or ip.is_unspecified:
            return False, f"予約 IP に解決される ({ip})"

    return True, "ok"
