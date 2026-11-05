const BOOKING_WINDOW_DAYS = 14;
const DAY_MS = 24 * 60 * 60 * 1000;

export function isBookableDate(value, now = new Date(), timeZone = "America/Sao_Paulo") {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  const candidate = new Date(Date.UTC(year, month - 1, day));
  if (candidate.getUTCFullYear() !== year || candidate.getUTCMonth() !== month - 1 || candidate.getUTCDate() !== day) return false;
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(now);
  const part = (type) => Number(parts.find((item) => item.type === type).value);
  const today = Date.UTC(part("year"), part("month") - 1, part("day"));
  const dayDifference = (candidate.getTime() - today) / DAY_MS;
  if (dayDifference < 0 || dayDifference > BOOKING_WINDOW_DAYS) return false;
  return true;
}

export function bookingDateBounds(now = new Date()) {
  const min = localDateInZone(now);
  const end = new Date(`${min}T00:00:00Z`);
  end.setUTCDate(end.getUTCDate() + BOOKING_WINDOW_DAYS);
  return { min, max: end.toISOString().slice(0, 10) };
}

function wallTime(now) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).formatToParts(now);
  const part = (type) => Number(parts.find((item) => item.type === type).value);
  return Date.UTC(part("year"), part("month") - 1, part("day"), part("hour"), part("minute"), part("second"), now.getUTCMilliseconds());
}

// API naive datetimes are São Paulo wall time; explicit offsets are normalized there.
export function isBookableDateTime(value, now = new Date()) {
  const match = /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})?$/.exec(value || "");
  if (!match || !isBookableDate(match[1], new Date(`${match[1]}T12:00:00-03:00`)) || +match[2] > 23 || +match[3] > 59 || +match[4] > 59) return false;
  const parsed = new Date(match[6] ? value : `${value}Z`);
  if (!Number.isFinite(parsed.getTime())) return false;
  const candidate = match[6] ? wallTime(parsed) : parsed.getTime();
  const current = wallTime(now);
  return candidate >= current && candidate <= current + BOOKING_WINDOW_DAYS * DAY_MS;
}

export function localDateInZone(now = new Date(), timeZone = "America/Sao_Paulo") {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(now);
  const part = (type) => parts.find((item) => item.type === type).value;
  return `${part("year")}-${part("month")}-${part("day")}`;
}
