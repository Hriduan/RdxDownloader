"""Public-network-only sockets inside each disposable extraction process.
This supplements, not replaces, an outbound firewall/container network policy.
"""
import ipaddress
import socket
from urllib.parse import urlsplit


def public_ip(value):
    try:
        address = ipaddress.ip_address(value.split('%', 1)[0])
        if isinstance(address, ipaddress.IPv6Address) and (address in ipaddress.ip_network('64:ff9b::/96') or address.sixtofour or address.teredo):
            return False
        if getattr(address, 'ipv4_mapped', None):
            address = address.ipv4_mapped
        return address.is_global and not (address.is_multicast or address.is_unspecified)
    except ValueError:
        return False


def validate_url(url, resolve=True):
    if not isinstance(url, str) or not 1 <= len(url) <= 2048 or any(ord(c) < 32 for c in url):
        raise ValueError('Use a valid public video URL.')
    try:
        u = urlsplit(url)
        if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password:
            raise ValueError()
        if u.port not in (None, 80, 443):
            raise ValueError()
        host = u.hostname.rstrip('.').lower()
        if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal', '.home', '.lan')):
            raise ValueError()
        try:
            ipaddress.ip_address(host)
        except ValueError:
            if '.' not in host:
                raise ValueError()
        else:
            if not public_ip(host):
                raise ValueError()
        if resolve:
            addresses = socket.getaddrinfo(host, u.port or (443 if u.scheme == 'https' else 80), type=socket.SOCK_STREAM)
            if not addresses or any(not public_ip(a[4][0]) for a in addresses):
                raise ValueError()
        return url
    except (ValueError, OSError, UnicodeError):
        raise ValueError('Only public HTTP/HTTPS links on standard ports are accepted.') from None


def install_socket_guard():
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def checked(address, family):
        if family not in (socket.AF_INET, socket.AF_INET6) or not isinstance(address, tuple):
            raise OSError('Non-Internet sockets are disabled in extraction workers.')
        host, port = address[:2]
        if int(port) not in (80, 443):
            raise OSError('Outbound port is not permitted.')
        # Resolve once, validate every answer, and connect to a numeric address.
        # This also checks redirect/CDN/extractor requests at the actual socket boundary.
        candidates = socket.getaddrinfo(host, port, family=family, type=socket.SOCK_STREAM)
        if not candidates or any(not public_ip(a[4][0]) for a in candidates):
            raise OSError('Private, reserved and local network destinations are blocked.')
        return candidates[0][4]

    def connect(sock, address):
        return original_connect(sock, checked(address, sock.family))

    def connect_ex(sock, address):
        return original_connect_ex(sock, checked(address, sock.family))

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
