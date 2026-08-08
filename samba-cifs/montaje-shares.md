# Montaje de Shares CIFS/SMB en Linux

Guía para montar shares de red Windows o Samba en un servidor Linux donde corre Hermes Agent.

## Requisitos previos

```bash
# Debian/Ubuntu
sudo apt install cifs-utils

# RHEL/CentOS
sudo dnf install cifs-utils
```

## Paso 1: Identificar los shares

Desde una máquina Windows:
- `\\192.168.1.100\Documentos` → unidad `W:`
- `\\192.168.1.100\Tecnico` → unidad `Y:`
- `\\192.168.1.100\Calidad` → unidad `V:`
- `\\192.168.1.100\Comercial` → unidad `X:`

Desde Linux, verificar accesibilidad:
```bash
smbclient -L //192.168.1.100 -U usuario
```

## Paso 2: Crear puntos de montaje

```bash
sudo mkdir -p /mnt/shares/{documentos,tecnico,calidad,comercial}
```

## Paso 3: Archivo de credenciales

Crear `/etc/samba/creds.txt` (protegido, solo root):
```
username=usuario_dominio
password=contraseña
domain=DOMINIO
```

```bash
sudo chmod 600 /etc/samba/creds.txt
```

## Paso 4: Montaje manual (prueba)

```bash
sudo mount -t cifs //192.168.1.100/Documentos /mnt/shares/documentos \
  -o credentials=/etc/samba/creds.txt,uid=1000,gid=1000,file_mode=0755,dir_mode=0755
```

Verificar:
```bash
ls /mnt/shares/documentos
df -h | grep shares
```

## Paso 5: Montaje automático (fstab)

Agregar a `/etc/fstab`:

```
# Shares de red
//192.168.1.100/Documentos  /mnt/shares/documentos  cifs  credentials=/etc/samba/creds.txt,uid=1000,gid=1000,file_mode=0755,dir_mode=0755,iocharset=utf8  0  0
//192.168.1.100/Tecnico    /mnt/shares/tecnico     cifs  credentials=/etc/samba/creds.txt,uid=1000,gid=1000,file_mode=0755,dir_mode=0755,iocharset=utf8  0  0
//192.168.1.100/Calidad    /mnt/shares/calidad     cifs  credentials=/etc/samba/creds.txt,uid=1000,gid=1000,file_mode=0755,dir_mode=0755,iocharset=utf8  0  0
//192.168.1.100/Comercial  /mnt/shares/comercial   cifs  credentials=/etc/samba/creds.txt,uid=1000,gid=1000,file_mode=0755,dir_mode=0755,iocharset=utf8  0  0
```

Aplicar sin reiniciar:
```bash
sudo mount -a
```

## Opciones útiles de montaje

| Opción | Efecto |
|--------|--------|
| `uid=1000,gid=1000` | Asignar propietario Linux a los archivos |
| `file_mode=0755,dir_mode=0755` | Permisos por defecto |
| `iocharset=utf8` | Soporte para tildes y ñ en nombres de archivo |
| `vers=3.0` | Forzar versión de protocolo SMB (útil si hay problemas de negociación) |
| `noatime` | No registrar tiempos de acceso (mejora rendimiento) |
| `ro` | Montaje solo lectura |
| `rw` | Montaje lectura/escritura |

## Permisos y seguridad

Si el share es de solo lectura para el usuario de Hermes pero se necesita que algunas carpetas sean escribibles, se puede configurar a nivel de Samba en el servidor Windows, no en el montaje CIFS.

**Recomendación:** Montar shares críticos como `ro` (solo lectura) y usar un share separado para entregables/escritura.

## Monitoreo de conectividad

Agregar un cron watchdog que verifique que los montajes estén activos:

```bash
#!/bin/bash
# watchdog-cifs.sh
for mount in /mnt/shares/*/; do
  if ! mountpoint -q "$mount"; then
    echo "WARNING: $mount no está montado" | systemd-cat -t watchdog-cifs
  fi
done
```

## Documentación oficial
- [Linux CIFS mount documentation](https://www.kernel.org/doc/Documentation/filesystems/cifs/)
- [Samba client documentation](https://www.samba.org/samba/docs/current/man-html/smbclient.1.html)
