# Migrar cron → systemd timers de usuario

Sustituye el crontab del usuario por timers de systemd. No requiere sudo (unidades de usuario).

## 1. Escribir el .service (el QUÉ)

`~/.config/systemd/user/<tarea>.service`:

```ini
[Unit]
Description=...
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/ruta/absoluta/al/script.sh
StandardOutput=journal
StandardError=journal
```

## 2. Escribir el .timer (el CUÁNDO)

`~/.config/systemd/user/<tarea>.timer`:

```ini
[Unit]
Description=...

[Timer]
OnCalendar=Tue *-*-* 08:00:00   # o varias líneas: 13:00:00 y 16:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

## 3. Activar y verificar

```bash
systemctl --user daemon-reload
systemctl --user enable --now <tarea>.timer
systemctl --user list-timers           # verificar NEXT
journalctl --user -u <tarea>.service   # logs centralizados
```

## 4. Retirar el crontab (atómico)

Quitar la línea del crontab EN EL MISMO paso en que se activa el timer (evita doble ejecución):

```bash
crontab -l > ~/backups/crontab.$(date +%Y%m%d).bak   # backup
crontab -r                                            # o editar para quitar solo las líneas migradas
```

## 5. Prueba real de la tarea

```bash
systemctl --user start <tarea>.service      # bloquea hasta terminar (Type=oneshot)
systemctl --user status <tarea>.service     # exit SUCCESS / FAILED
journalctl --user -u <tarea>.service -n 40
```

## Dependencia con un host remoto

`After=network-online.target` cubre la red local, pero NO espera a un host remoto. Para un script que hace `scp`/`ssh` contra un servidor que se apaga de noche, usar un wrapper con reintento acotado:

```bash
for i in $(seq 1 15); do
    /ruta/script.sh && exit 0
    sleep 60
done
exit 1
```
