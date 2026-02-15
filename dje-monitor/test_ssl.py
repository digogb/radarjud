import ssl
import socket

hostname = 'esaj.tjce.jus.br'
context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

try:
    with socket.create_connection((hostname, 443)) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            print("Versão SSL:", ssock.version())
            print("Cifra:", ssock.cipher())
except Exception as e:
    print(f"Erro: {e}")
