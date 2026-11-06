import socket


def get_local_ips():
    """Local IPv4 addresses of this computer - to put into the firmware config."""
    ips = []
    try:
        _, _, ip_list = socket.gethostbyname_ex(socket.gethostname())
        for ip in ip_list:
            if ip.startswith(("192.168.", "10.", "172.")):
                ips.append(ip)
    except Exception:
        pass
    if "127.0.0.1" not in ips:
        ips.append("127.0.0.1")
    return ips
