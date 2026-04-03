export function buildIsoDateTime(dateValue: string, timeValue: string) {
  return new Date(`${dateValue}T${timeValue}`).toISOString();
}

export function buildEventEndIso(dateValue: string, startTimeValue: string, endTimeValue: string) {
  const start = new Date(`${dateValue}T${startTimeValue}`);
  if (endTimeValue) {
    const end = new Date(`${dateValue}T${endTimeValue}`);
    if (end.getTime() > start.getTime()) {
      return end.toISOString();
    }
  }

  const fallback = new Date(start);
  fallback.setHours(fallback.getHours() + 1);
  return fallback.toISOString();
}

export function toDateInputValue(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function toTimeInputValue(date: Date) {
  return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit", hour12: false });
}
