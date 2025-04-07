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

    def descargar_archivo_gzipped(self, remote_path, local_path):
        """Descarga y descomprime archivos comprimidos .gz"""
        if self._es_archivo_texto(remote_path):
            temp_path = f"{local_path}.gz"
            self.sftp.get(remote_path, temp_path)
            self._descomprimir_archivo(temp_path, local_path)
        else:
            self.sftp.get(remote_path, local_path)

    def descargar_archivo(self, remote_path, local_path):
        """Descarga directa sin compresión"""
        self.sftp.get(remote_path, local_path)

    # Modificar en la clase SecureSFTP
    def eliminar_archivo_remoto(self, remote_path):
        """Elimina un archivo en el servidor remoto"""
        if self.sftp:
            self.sftp.remove(remote_path)  # Acceder al método del SFTPClient
        else:
            raise Exception("Conexión SFTP no establecida")

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
    """Fase 1: Generar metadata en ruta configurable"""  
    print("\n[FASE 1] Generando metadata remota...")  
    ssh = paramiko.SSHClient()  
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  
    ssh.connect(  
        os.getenv('SSH_HOST'),  
        username=os.getenv('SSH_USER'),  
        password=os.getenv('SSH_PASS')  
    )  
    
    # Usar variable de entorno para la ruta  
    metadata_path = os.getenv('REMOTE_METADATA_PATH', '/tmp/filelist.txt.gz')  
    dir_path = os.path.dirname(metadata_path)  
    
    # Comando seguro: crear directorio si no existe y generar metadata  
    comando = f"mkdir -p {dir_path} && find {os.getenv('REMOTE_DIR')} -type f -printf '%s %TY-%Tm-%Td %TH:%TM:%.2TS %p\n' | gzip -c > {metadata_path}"  
    
    ssh.exec_command(comando)  
    ssh.close()  
    print(f"✓ Listado generado en {metadata_path}")  


def descargar_metadata():  
    """Fase 2: Descargar metadata desde ruta configurable"""  
    print("\n[FASE 2] Descargando metadata...")  
    metadata_path = os.getenv('REMOTE_METADATA_PATH', '/tmp/filelist.txt.gz')  
    
    with SecureSFTP() as sftp:  
        sftp.descargar_archivo_gzipped(metadata_path, 'filelist.txt.gz')  
    
    with gzip.open('filelist.txt.gz', 'rb') as f:  
        with open('filelist.txt', 'wb') as out:  
            out.write(f.read())  
    os.remove('filelist.txt.gz')  
    print(f"✓ Metadata descargada desde {metadata_path}")

    # Opcional: Al final de descargar_metadata  
    # with SecureSFTP() as sftp:
      #  sftp.eliminar_archivo_remoto(metadata_path) 
    # print(f"✓ Metadata eliminada del servidor")

def imprimir_cambios(cambios):      
    print(f"\nArchivos modificados ({len(cambios)}):")
    for cambio in cambios:
        if 'local_modified' in cambio:
            print(f"✓ {cambio['path']} [Remote: {cambio['remote_modified']} | Local: {cambio['local_modified']}]")
        else:
            print(f"✓ {cambio['path']} (nuevo)")


def comparar_archivos():
    """Fase 3: Comparar archivos locales/remotos"""
    print("\n[FASE 3] Comparando archivos...")
    server_files = {}
    remote_dir = os.getenv('REMOTE_DIR').rstrip('/')  # Normalizar REMOTE_DIR
     # Normalizar rutas a ignorar (evitar barras inconsistentes)
    ignore_paths = [
        os.path.normpath(p.strip()) 
        for p in os.getenv('IGNORE_PATHS', '').split('|')
    ]
    
    with open('filelist.txt', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(' ', 3)
            if len(parts) == 4:
                size, date_str, time_str, path = parts
                relative_path = os.path.normpath(path[len(remote_dir):].lstrip('/'))
                
                # Verificar si la ruta comienza con algún patrón ignorado
                if any(
                    os.path.commonpath([relative_path, ignored]) == ignored
                    for ignored in ignore_paths
                ):
                    continue

                server_files[relative_path] = {
                    'size': int(size),
                    'modified': datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
                }
    
    cambios = []
    local_dir = os.getenv('LOCAL_DIR')
    
    for relative_path, meta in server_files.items():
        local_path = os.path.join(local_dir, relative_path)
        cambio = {
            'path': relative_path,  # Guardar ruta relativa
            'remote_modified': meta['modified'],
        }
        
        if not os.path.exists(local_path):
            cambios.append(cambio)
        else:
            stat = os.stat(local_path)
            local_modified = datetime.fromtimestamp(stat.st_mtime)
            
            if (stat.st_size != meta['size'] or 
                local_modified < meta['modified']):
                cambio['local_modified'] = local_modified
                cambios.append(cambio)
    
    return cambios


def descargar_archivos(cambios):
    """Fase 4: Descarga archivos nuevos o modificados"""
    print("\n[FASE 4] Descargando cambios...")
    remote_dir = os.getenv('REMOTE_DIR').rstrip('/')  # Normalizar REMOTE_DIR
    
    with SecureSFTP() as sftp:
        for cambio in cambios:
            relative_path = cambio['path']
            # Convertir ruta local a formato UNIX para SFTP
            remote_path = f"{remote_dir}/{relative_path.replace(os.sep, '/')}"  # ← Conversión clave
            # Normalizar ruta local (convertir a barras adecuadas para el sistema)
            local_path = os.path.normpath(
                os.path.join(os.getenv('LOCAL_DIR'), relative_path)
            )
            
            # Crear directorios necesarios
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            print(f"Descargando {relative_path}...")
            try:
                sftp.descargar_archivo(remote_path, local_path)
                
                # Aplicar fecha/hora desde metadata
                mod_time = cambio['remote_modified'].timestamp()
                os.utime(local_path, (mod_time, mod_time))
                
                print(f"✓ {relative_path} [Fecha: {cambio['remote_modified'].strftime('%Y-%m-%d %H:%M:%S')}]")
            except Exception as e:
                print(f"✗ Error: {str(e)}")



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', type=int, choices=[1,2,3,4], help='Ejecutar fase específica')
    args = parser.parse_args()

    if args.phase == 1:
        generar_metadata_remota()
    elif args.phase == 2:
        descargar_metadata()
    elif args.phase == 3:
        cambios = comparar_archivos()
        imprimir_cambios(cambios)
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
