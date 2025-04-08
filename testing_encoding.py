import os
import paramiko
import urllib.parse
from dotenv import load_dotenv
import unicodedata

# Cargar variables de conexión
load_dotenv()

REMOTE_DIR = os.getenv('REMOTE_DIR')
LOCAL_DIR = os.getenv('LOCAL_DIR')
SSH_HOST = os.getenv('SSH_HOST')
SSH_USER = os.getenv('SSH_USER')
SSH_KEY = os.getenv('SSH_KEY')

def sanitizar_nombre_windows(nombre):
    """Reemplaza caracteres prohibidos en Windows"""
    caracteres_prohibidos = r'<>:"/\|?*'
    return ''.join('_' if char in caracteres_prohibidos else char for char in nombre)

def generar_variantes_ruta(original_path):
    """Genera diferentes versiones de la ruta para testing"""


    partes = original_path.split('/')
    nombre_archivo = partes[-1]

    return [
       # 1. Codificación URL completa (mejorada)
        '/'.join(partes[:-1] + [urllib.parse.quote(nombre_archivo, safe='')]),
        
        # 2. Codificación parcial mejorada
        '/'.join(urllib.parse.quote(part, safe='/') for part in partes),
        
        # 3. Normalización Unicode NFC (no NFD)
        '/'.join(partes[:-1] + [unicodedata.normalize('NFC', nombre_archivo)]),
        
        # 4. Codificación URL + Normalización NFC
        '/'.join(
            urllib.parse.quote(unicodedata.normalize('NFC', part), safe='/') 
            for part in partes
        ),
        
        # 5. Escapado manual de caracteres especiales
        original_path.replace(' ', '%20').replace(':', '%3A').replace('?', '%3F').replace('&', '%26').replace('=', '%3D').replace('#', '%23')
        .replace('!', '%21').replace('@', '%40').replace('$', '%24').replace('%', '%25').replace('^', '%5E').replace('&', '%26').replace('*', '%2A')
        .replace('(', '%28').replace(')', '%29').replace('+', '%2B').replace('{', '%7B').replace('}', '%7D').replace('[', '%5B').replace(']', '%5D')
        .replace(';', '%3B').replace('\'', '%27').replace('"', '%22').replace('<', '%3C').replace('>', '%3E').replace(',', '%2C').replace('.', '%2E')
        .replace('~', '%7E').replace('`', '%60').replace('|', '%7C').replace('\\', '%5C').replace('/', '%2F').replace('-', '%2D').replace('_', '%5F')
        .replace('?', '%3F').replace('=', '%3D').replace('+', '%2B').replace('@', '%40').replace('#', '%23').replace('$', '%24').replace('%', '%25')
        .replace('¿', '%BF').replace('¡', '%A1').replace('ñ', '%F1').replace('Ñ', '%D1'),
    ]

def test_descarga(remote_path, local_name):
    """Prueba diferentes métodos de descarga"""
    resultados = {}
    variantes = generar_variantes_ruta(remote_path)

    print(variantes)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
            hostname=os.getenv('SSH_HOST'),
            port=int(os.getenv('SFTP_PORT', 22)),
            username=os.getenv('SSH_USER'),
            password=os.getenv('SSH_PASS')
        )
    sftp = ssh.open_sftp()
    
    for i, variante in enumerate(variantes, 1):
        try:
            local_path = os.path.join(LOCAL_DIR, f"test_{i}_{sanitizar_nombre_windows(local_name)}")
            sftp.get(variante, local_path)
            resultados[f"Variante {i}"] = "✓ Éxito"
        except Exception as e:
            resultados[f"Variante {i}"] = f"✗ Error: {str(e)}"
    
    sftp.close()
    ssh.close()
    return resultados

if __name__ == "__main__":
    # Archivo de prueba con caracteres especiales
    ARCHIVO_PRUEBA = "árbol:(dos).txt"
    
    print("Iniciando pruebas de descarga SFTP...\n")
    resultados = test_descarga(f"{REMOTE_DIR}/{ARCHIVO_PRUEBA}", os.path.basename(ARCHIVO_PRUEBA))
    
    print("Resultados de las pruebas:")
    for metodo, resultado in resultados.items():
        print(f"{metodo}: {resultado}")
