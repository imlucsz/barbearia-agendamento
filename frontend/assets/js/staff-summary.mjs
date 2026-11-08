export function summarizeDay(rows, selectedDay, now = new Date()) {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(now);
  const part = name => parts.find(p => p.type === name).value;
  const today = `${part('year')}-${part('month')}-${part('day')}`;
  const time = `${part('hour')}:${part('minute')}`;
  const pending = rows.filter(row => ['confirmado', 'pendente'].includes(row.status));
  const next = selectedDay < today ? null : pending.filter(row => /^\d{2}:\d{2}$/.test(row.horario) && (selectedDay > today || row.horario >= time)).sort((a, b) => a.horario.localeCompare(b.horario))[0] || null;
  return { total: rows.length, pending: pending.length, completed: rows.filter(row => ['concluido', 'avaliado'].includes(row.status)).length, next };
}
