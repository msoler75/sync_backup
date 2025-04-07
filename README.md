# SYNC BACKUP

## Herramienta de Backup Sincronizado

Este script permite hacer un backup de carpetas y archivos de un servidor a la máquina local. 

Lo hace optimizando la detección de cambios y la transferencia mediante compresión selectiva. Ideal para mantener copias de seguridad eficientes y actualizadas.  

## Motivo de su creación

Necesitaba hacer una copia periódica de una estructura de carpetas gigante, y lo hacía a través de FTP con Filezilla. El tiempo de comparación (listar) de directorios y archivos era enorme, así que me vi obligado a diseñar una forma más eficiente. 

Ahora con este script se detecta muy rápidamente qué archivos son nuevos o han cambiado y los descarga automáticamente.

---
<!--  -->
### **Instalación y Configuración**  

**Requisitos del Sistema**  
- **Python 3.8+**  
- **Dependencias**:  
  ```bash  
  pip install python-dotenv paramiko 
  ```

### **Archivo de Configuración (.env)**  
```env  
# Configuración básica  
LOCAL_DIR=./storage/          # Ruta local para almacenar archivos  
SSH_HOST=tu_servidor.com      # Host del servidor SSH/SFTP  
SSH_USER=usuario_ssh          # Usuario SSH  
SSH_PASS=password_ssh         # Contraseña SSH  
REMOTE_DIR=/ruta/remota/      # Directorio remoto a sincronizar  

# Configuración avanzada SFTP  
SFTP_PORT=22                  # Puerto SFTP (predeterminado: 22)  
COMPRESSION_LEVEL=9           # Nivel de compresión para archivos de texto (1-9)  
```

---

### **Modo de Uso**  

**Ejecución Completa**  
```bash  
python3 sync.py  
```

**Ejecución por Fases**  
| Fase | Descripción | Comando |  
|------|-------------|---------|  
| **1** | Genera metadatos de archivos en el servidor | `python3 sync.py --phase 1` |  
| **2** | Descarga metadatos al entorno local | `python3 sync.py --phase 2` |  
| **3** | Compara archivos locales y remotos | `python3 sync.py --phase 3` |  
| **4** | Descarga archivos nuevos/modificados | `python3 sync.py --phase 4` |  

---

### **Ambiente de Pruebas**  

**1. Preparar Servidor**  
```bash  
# Crear estructura de prueba  
mkdir -p /ruta/remota/{docs,images}  
echo "v1" > /ruta/remota/test.txt  
echo "img" > /ruta/remota/images/logo.png  
```

**2. Simular Cambios**  
```bash  
# Modificar archivo en servidor  
echo "nuevo" >> /ruta/remota/test.txt  

# Verificar detección de cambios  
python3 sync.py --phase 3  
```

**3. Forzar Actualización Local**  
```bash  
# Crear archivo local obsoleto  
touch -d '2023-01-01' storage/test.txt  

# Ejecutar descarga de cambios  
python3 sync.py --phase 4  
```

---

### **Flujo de Verificación**  

| Fase | Verificación |  
|------|--------------|  
| **1** | Confirmar creación de `/tmp/filelist.txt` en servidor |  
| **2** | Validar existencia de `metadata.zip` y contenido de `filelist.txt` |  
| **3** | Revisar salida de consola para detectar archivos modificados |  
| **4** | Comprobar fechas y contenido de archivos en `LOCAL_DIR` |  

---

### **Ventajas del Sistema**  
- **Optimización de Red**: Compresión automática de archivos de texto (`.txt`, `.csv`, `.json`, etc.).  
- **Modularidad**: Fases independientes para pruebas o integración en pipelines.  
- **Transparencia**: Logs detallados en consola y validación visual de cambios.  
- **Seguridad**: Conexión SFTP encriptada y gestión de credenciales mediante `.env`.  

---

**Nota Final**: Para entornos productivos, restringir permisos del archivo `.env`:  
```bash  
chmod 600 .env  
```
