# Lecciones Aprendidas — Samba/CIFS + Hermes

## 1. CIFS no es para búsqueda en tiempo real

**Problema:** Una búsqueda recursiva (`find` o `ls -R`) sobre un share CIFS montado puede tomar 30-120 segundos. Con 120,000+ archivos, el protocolo SMB simplemente no está diseñado para esto.

**Solución:** Indexar localmente con SQLite FTS5. La búsqueda pasa de 60 segundos a <50ms.

```
Búsqueda directa CIFS:  ████████████████████████████████ 60s
Índice JSON secuencial: ████ 5s
Índice SQLite FTS5:     █ <50ms
```

---

## 2. Bloqueos de red intermitentes

**Problema:** En redes locales con switches domésticos o configuraciones ARP inestables, los shares pueden aparecer como "no disponibles" aunque el servidor esté encendido. ARP muestra REACHABLE pero TCP (ping/SSH/SMB) falla temporalmente.

**Síntomas:**
- `ls /mnt/shares/` se queda colgado
- El índice falla a media ejecución
- `mount` muestra el share pero `df` no responde

**Solución:**
- Agregar `vers=3.0` a las opciones de montaje (fuerza una versión específica de SMB)
- Implementar watchdog que detecte shares caídos
- Usar timeout en los comandos de indexación
- Agregar `soft` y `timeo=10` en opciones de montaje para que las operaciones fallen rápido en vez de colgarse

```bash
# /etc/fstab con opciones de resiliencia
//192.168.1.100/Documentos /mnt/shares/documentos cifs credentials=/etc/samba/creds.txt,uid=1000,gid=1000,vers=3.0,soft,timeo=10 0 0
```

---

## 3. Permisos Samba vs permisos Linux

**Problema:** Los permisos de escritura se definen a nivel Samba (en el servidor Windows/NAS), no en el montaje CIFS. Montar con `rw` no garantiza poder escribir si el usuario Samba no tiene permisos.

**Solución:** Configurar los permisos en el servidor Samba/Windows. El montaje CIFS solo refleja los permisos del servidor.

**Verificación:**
```bash
# Probar escritura antes de asumir que funciona
touch /mnt/shares/documentos/test.txt && rm /mnt/shares/documentos/test.txt
```

---

## 4. La indexación nocturna falla si el NAS se apaga de noche

**Problema:** Programar la indexación de madrugada (2:00 AM) parece ideal ("cero actividad"), pero si el servidor NAS se apaga de noche (~8pm–7:30am), el cron falla con "No route to host". Además, diagnosticar por `ping` engaña: el NAS puede no responder ICMP (bloqueado por firewall) aunque SMB y SSH sí funcionen.

**Solución:** Indexar en horas laborales, dos veces al día:
- Indexación: 13:00 y 16:00 (NAS encendido; captura los cambios de la mañana y de la tarde)
- Backup diario: 18:00 (tras la segunda indexación)

**Diagnóstico correcto:** verificar conectividad por puertos TCP (445 SMB, 22 SSH), no por `ping`.

---

## 5. `.indexrules` debe mantenerse sincronizado

**Problema:** Cuando se agregan nuevas carpetas o shares, si no se actualiza `.indexrules`, el índice queda incompleto y las búsquedas devuelven resultados parciales.

**Solución:** 
- Documentar `.indexrules` como parte de la configuración de infraestructura
- Revisar trimestralmente que las particiones reflejen la estructura real de los shares
- Usar `hermes-indexer --output <dir> --force` después de cada cambio

---

## 6. Nombres de archivo con caracteres especiales

**Problema:** Archivos con tildes, ñ, espacios o caracteres Unicode pueden causar errores de codificación si el montaje CIFS no especifica `iocharset=utf8`.

**Solución:** Siempre incluir `iocharset=utf8` en las opciones de montaje.

---

## 7. Credenciales en texto plano

**Problema:** El archivo de credenciales CIFS (`/etc/samba/creds.txt`) contiene la contraseña en texto plano.

**Mitigación:**
- `chmod 600` — solo readable por root
- Usar una cuenta de servicio con permisos mínimos (solo lectura a los shares necesarios)
- No versionar el archivo de credenciales en git
- Rotar la contraseña periódicamente

---

## 8. SQLite FTS5 tiene límite de tamaño

**Problema:** Con 120,000+ archivos, la base SQLite FTS5 puede crecer a 60-80 MB. Para shares más grandes (500,000+ archivos), puede volverse lenta.

**Solución:** Para shares muy grandes:
- Particionar por año o por tipo de documento
- Usar múltiples bases SQLite (una por partición)
- Considerar motores de búsqueda más pesados (Elasticsearch, Meilisearch) para escalas mayores

---

## 9. Watchdog para montajes caídos

**Problema:** Si un share se desmonta (reinicio del servidor Windows, corte de red), Hermes pierde acceso sin aviso.

**Solución:** Script watchdog que verifica periódicamente:

```bash
#!/bin/bash
# watchdog-cifs.sh — ejecutar cada 5 minutos vía cron
for mount in /mnt/shares/documentos /mnt/shares/tecnico /mnt/shares/calidad; do
  if ! mountpoint -q "$mount"; then
    echo "ALERTA: $mount no está montado. Intentando remontar..."
    sudo mount "$mount"
  fi
done
```

---

## 10. Documentación de la topología

Es crucial documentar:

| Elemento | Ejemplo anonimizado |
|----------|-------------------|
| Servidor de archivos | `192.168.1.100` (Windows Server) |
| Shares y letras de unidad | `W:` = Documentos, `Y:` = Técnico, `V:` = Calidad |
| Usuario de servicio | `hermes_svc` (solo lectura) |
| Ruta de índices | `/opt/hermes/indices/` |
| Ruta de montaje | `/mnt/shares/` |

Esto evita confusión cuando alguien nuevo se integra al equipo.

---

## Resumen rápido para depuración

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| `ls` colgado en share | Conexión CIFS interrumpida | `umount -l` + `mount -a` |
| Error "Permission denied" | Permisos Samba | Verificar en servidor remoto |
| Archivos con nombres rotos | Falta `iocharset=utf8` | Agregar a opciones fstab |
| Búsqueda lenta (>30s) | Índice desactualizado | `hermes-indexer --build-db` |
| Share no monta al boot | Orden de red incorrecto | Agregar `_netdev,x-systemd.automount` |
| `df` colgado | Share caído sin `soft` | Agregar `soft,timeo=10` |
