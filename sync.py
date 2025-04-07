import os
import paramiko
import gzip
from datetime import datetime
from dotenv import load_dotenv
import argparse

# Cargar variables de entorno
load_dotenv()

class SecureSFTP:
    def __init__(self):
        self.ssh = paramiko.SSHClient()
        self.sftp = None
        
    def connect(self):
        """Establece conexión SFTP segura"""
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(
            hostname=os.getenv('SSH_HOST'),
            port=int(os.getenv('SFTP_PORT', 22)),
            username=os.getenv('SSH_USER'),
            password=os.getenv('SSH_PASS')
        )
        self.sftp = self.ssh.open_sftp()
        return self

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()

    def descargar_archivo(self, remote_path, local_path):
        """Descarga y descomprime archivos de texto"""
        if self._es_archivo_texto(remote_path):
            temp_path = f"{local_path}.gz"
            self.sftp.get(remote_path, temp_path)
            self._descomprimir_archivo(temp_path, local_path)
        else:
            self.sftp.get(remote_path, local_path)

    def _es_archivo_texto(self, filename):
        """Detecta si el archivo es texto según extensión"""
        extensiones_texto = ['.txt', '.log', '.csv', '.json', '.xml', '.html', '.js', '.css', '.py', '.md',
                             '.php', '.vue', '.java', '.c', '.cpp', '.h', '.sql', '.yaml', '.yml']
        # Agregar más extensiones según sea necesario
        return any(filename.lower().endswith(ext) for ext in extensiones_texto)

    def _descomprimir_archivo(self, src, dest):
        """Descomprime archivos .gz"""
        with gzip.open(src, 'rb') as f_in:
            with open(dest, 'wb') as f_out:
                f_out.write(f_in.read())
        os.remove(src)

def generar_metadata_remota():
    """Fase 1: Generar listado en servidor"""
    print("\n[FASE 1] Generando metadata remota...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        os.getenv('SSH_HOST'),
        username=os.getenv('SSH_USER'),
        password=os.getenv('SSH_PASS')
    )
    
    comando = f"find {os.getenv('REMOTE_DIR')} -type f -printf '%s %TY-%Tm-%Td %TH:%TM:%.2TS %p\n' | gzip -c > /tmp/filelist.txt.gz"
    ssh.exec_command(comando)
    ssh.close()
    print("✓ Listado generado en servidor")

def descargar_metadata():
    """Fase 2: Descargar metadata comprimida"""
    print("\n[FASE 2] Descargando metadata...")
    with SecureSFTP() as sftp:
        sftp.descargar_archivo('/tmp/filelist.txt.gz', 'filelist.txt.gz')
    
    with gzip.open('filelist.txt.gz', 'rb') as f:
        with open('filelist.txt', 'wb') as out:
            out.write(f.read())
    os.remove('filelist.txt.gz')
    print("✓ Metadata descargada y descomprimida")

def comparar_archivos():
    """Fase 3: Comparar archivos locales/remotos"""
    print("\n[FASE 3] Comparando archivos...")
    server_files = {}
    
    with open('filelist.txt') as f:
        for line in f:
            parts = line.strip().split(' ', 3)
            if len(parts) == 4:
                size, date_str, time_str, path = parts
                server_files[path] = {
                    'size': int(size),
                    'modified': datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S.%f")
                }
    
    cambios = []
    local_dir = os.getenv('LOCAL_DIR')
    for path, meta in server_files.items():
        local_path = os.path.join(local_dir, path)
        
        if not os.path.exists(local_path):
            cambios.append(path)
        else:
            stat = os.stat(local_path)
            if (stat.st_size != meta['size'] or 
                datetime.fromtimestamp(stat.st_mtime) < meta['modified']):
                cambios.append(path)
    
    print(f"\nArchivos modificados ({len(cambios)}):")
    for archivo in cambios:
        print(f" - {archivo}")
    
    return cambios

def descargar_archivos(archivos):
    """Fase 4: Descargar actualizaciones"""
    print("\n[FASE 4] Descargando cambios...")
    with SecureSFTP() as sftp:
        for archivo in archivos:
            local_path = os.path.join(os.getenv('LOCAL_DIR'), archivo)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            remote_path = f"{os.getenv('REMOTE_DIR')}/{archivo}"
            print(f"Descargando {archivo}...")
            sftp.descargar_archivo(remote_path, local_path)
            print(f"✓ {archivo} {'(comprimido)' if sftp._es_archivo_texto(archivo) else ''}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', type=int, choices=[1,2,3,4], help='Ejecutar fase específica')
    args = parser.parse_args()

    if args.phase == 1:
        generar_metadata_remota()
    elif args.phase == 2:
        descargar_metadata()
    elif args.phase == 3:
        comparar_archivos()
    elif args.phase == 4:
        cambios = comparar_archivos()
        if cambios:
            descargar_archivos(cambios)
    else:
        generar_metadata_remota()
        descargar_metadata()
        cambios = comparar_archivos()
        if cambios:
            descargar_archivos(cambios)

if __name__ == "__main__":
    main()
