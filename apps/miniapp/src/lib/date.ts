function buildLocalDate(dateValue: string, timeValue: string) {
  const [yearRaw, monthRaw, dayRaw] = dateValue.split("-");
  const [hoursRaw, minutesRaw] = timeValue.split(":");
  const year = Number(yearRaw);
  const month = Number(monthRaw);
  const day = Number(dayRaw);
  const hours = Number(hoursRaw);
  const minutes = Number(minutesRaw);
  const localDate = new Date(year, month - 1, day, hours, minutes, 0, 0);
  if (
    Number.isNaN(localDate.getTime())
    || localDate.getFullYear() !== year
    || localDate.getMonth() !== month - 1
    || localDate.getDate() !== day
  ) {
    throw new Error("Некорректная дата или время");
  }
  return localDate;
}

export function buildIsoFromDateTimeLocal(value: string) {
  const [dateValue, timeValueRaw] = value.split("T");
  const timeValue = timeValueRaw?.slice(0, 5);
  if (!dateValue || !timeValue) {
    throw new Error("Некорректная дата и время");
  }
  return buildLocalDate(dateValue, timeValue).toISOString();
}

export function buildIsoDateTime(dateValue: string, timeValue: string) {
  return buildLocalDate(dateValue, timeValue).toISOString();
}

export function buildEventEndIso(dateValue: string, startTimeValue: string, endTimeValue: string) {
  const start = buildLocalDate(dateValue, startTimeValue);
  if (endTimeValue) {
    const end = buildLocalDate(dateValue, endTimeValue);
    if (end.getTime() > start.getTime()) {
      return end.toISOString();
    }
  }

  const fallback = new Date(start);
  fallback.setHours(fallback.getHours() + 1);
  return fallback.toISOString();
}

export function toDateInputValue(date: Date) {
  const year = String(date.getFullYear()).padStart(4, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function toTimeInputValue(date: Date) {
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${hours}:${minutes}`;
}
