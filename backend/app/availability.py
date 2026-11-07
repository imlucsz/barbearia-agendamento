"""Bounded read-only projections; all slots use the reservation validator."""
from datetime import datetime, timedelta

from fastapi import HTTPException

from app.booking import (
    ACTIVE_APPOINTMENT_STATUSES, SLOT_INTERVAL_MINUTES, schedule_bounds,
    validate_slot_against_loaded_data,
)
from app.models.user import (
    Appointment, BarbearioServico, BloqueioHorario, JornadaTrabalho, RoleEnum, Service, User,
)


def availability_days(db, service_id, barber_id, first_day, last_day, now, appointment=None):
    service = db.query(Service).filter(Service.id == service_id).first()
    if service is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    duration = appointment.duracao_minutos if appointment is not None else service.duracao_minutos
    exclude_id = appointment.id if appointment is not None else None
    barbers_query = db.query(User).join(
        BarbearioServico, BarbearioServico.barbeiro_id == User.id,
    ).filter(User.role == RoleEnum.BARBEIRO, User.ativo.is_(True),
             User.bloqueado.is_(False), BarbearioServico.service_id == service_id)
    if barber_id is not None:
        barbers_query = barbers_query.filter(User.id == barber_id)
    barbers = barbers_query.all()
    if barber_id is not None and not barbers:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado ou não realiza este serviço")
    ids = [barber.id for barber in barbers]
    schedules = {}
    for row in db.query(JornadaTrabalho).filter(
            JornadaTrabalho.barbeiro_id.in_(ids), JornadaTrabalho.ativo.is_(True),
        ).order_by(JornadaTrabalho.hora_inicio).all() if ids else []:
        schedules.setdefault((row.barbeiro_id, row.dia_semana), []).append(row)
    first = datetime.combine(first_day, datetime.min.time())
    end = datetime.combine(last_day + timedelta(days=1), datetime.min.time())
    blocks = db.query(BloqueioHorario).filter(
        BloqueioHorario.barbeiro_id.in_(ids), BloqueioHorario.ativo.is_(True),
        BloqueioHorario.inicio < end, BloqueioHorario.fim > first,
    ).all() if ids else []
    appointments_query = db.query(Appointment).filter(
        Appointment.barbeiro_id.in_(ids),
        Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
        # Appointment snapshots are bounded to 1440 minutes by the API contract.
        # Retain starts on the previous day that can overlap today's opening.
        Appointment.data_hora >= first - timedelta(days=1),
        Appointment.data_hora < end,
    )
    if exclude_id is not None:
        appointments_query = appointments_query.filter(Appointment.id != exclude_id)
    appointments = appointments_query.all() if ids else []
    days = []
    day = first_day
    while day <= last_day:
        slots, working, unblocked = [], False, False
        for barber in barbers:
            for schedule in schedules.get((barber.id, (day.weekday() + 1) % 7), []):
                working = True
                opening, closing = schedule_bounds(day, schedule)
                barber_blocks = [b for b in blocks if b.barbeiro_id == barber.id]
                barber_appointments = [a for a in appointments if a.barbeiro_id == barber.id]
                # Merge overlapping/adjacent blocks to distinguish a day off from a full agenda.
                cursor = opening
                for block in sorted(barber_blocks, key=lambda b: b.inicio):
                    if block.fim <= cursor:
                        continue
                    if block.inicio > cursor:
                        break
                    cursor = max(cursor, block.fim)
                unblocked = unblocked or cursor < closing
                slot = opening
                while slot + timedelta(minutes=duration) <= closing:
                    try:
                        valid = validate_slot_against_loaded_data(
                            service, barber.id, slot, schedule=schedule, blocks=barber_blocks,
                            appointments=barber_appointments, now=now,
                            duration_minutes=duration,
                        )
                        slots.append({"horario": valid.strftime("%H:%M"),
                                      "data_hora": valid.isoformat(), "barbeiro_id": barber.id})
                    except HTTPException as exc:
                        if exc.status_code not in (400, 409):
                            raise
                    slot += timedelta(minutes=SLOT_INTERVAL_MINUTES)
        slots = list({(s["barbeiro_id"], s["data_hora"]): s for s in slots}.values())
        state = "available" if slots else "off" if not working else "full" if unblocked else "blocked"
        days.append({"date": day.isoformat(), "working": working, "status": state, "slots": slots})
        day += timedelta(days=1)
    return days
