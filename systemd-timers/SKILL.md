---
name: hermes-skills/systemd-timers
description: Use when scheduling recurring Linux tasks robustly with systemd timers instead of cron.
---

# Programación robusta de tareas con Systemd Timers

Cuándo usar systemd timers en vez de cron: cuando las tareas necesitan recuperarse tras un apagado (`Persistent=true`), logs centralizados (journald) o dependencias (`network-online.target`, discos montados).

## Documentos de referencia

| Documento | Cuándo cargar |
|-----------|---------------|
| `migracion-cron.md` | Migrar un crontab existente a timers |
| `lecciones-aprendidas.md` | Pitfalls y soluciones |

## Reglas rápidas

- **`Persistent=true`** recupera la última corrida perdida tras un apagón (no todas).
- **Logs:** `journalctl --user -u <unidad>` — sin redirecciones manuales.
- **Activar:** `systemctl --user enable --now <tarea>.timer` (nunca `start` a secas).
- **Sin sesión de login:** `loginctl enable-linger <usuario>`.
- **Editar:** `systemctl --user daemon-reload` después de tocar `.service`/`.timer`.

## Anatomía (dos archivos por tarea)

`<tarea>.service` (el QUÉ) + `<tarea>.timer` (el CUÁNDO), en `~/.config/systemd/user/`. Ver `migracion-cron.md`.
