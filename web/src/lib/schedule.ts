import type { DayType, ScheduleDay, ValidationIssue } from "./api";

export const dayTypeLabels: Record<DayType, string> = {
  work: "Работа",
  day_off: "Выходной",
  vacation: "Отпуск",
  holiday: "Праздник",
  unavailable: "Недоступен",
};

export function datesBetween(start: string, end: string): string[] {
  const dates: string[] = [];
  const current = parseDateUtc(start);
  const last = parseDateUtc(end);
  while (current <= last) {
    dates.push(formatIsoDateUtc(current));
    current.setUTCDate(current.getUTCDate() + 1);
  }
  return dates;
}

export function formatDate(date: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  }).format(parseDateUtc(date));
}

export function shortDate(date: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    timeZone: "UTC",
  }).format(parseDateUtc(date));
}

export function normalizeDay(day?: ScheduleDay): ScheduleDay {
  return {
    dayType: day?.dayType ?? "unavailable",
    status: day?.status ?? day?.dayType ?? "unavailable",
    segments: day?.segments?.length ? day.segments : [],
    employeeComment: day?.employeeComment ?? null,
    managerComment: day?.managerComment ?? null,
  };
}

export function defaultWorkDay(): ScheduleDay {
  return {
    dayType: "work",
    status: "work",
    segments: [{ start: "09:00", end: "18:00" }],
    employeeComment: null,
  };
}

export function issueMap(issues: ValidationIssue[]) {
  return issues.reduce<Record<string, ValidationIssue[]>>((acc, issue) => {
    const key = issue.date ?? "_global";
    acc[key] = [...(acc[key] ?? []), issue];
    return acc;
  }, {});
}

export function totalEmployeesAtHour(day: Record<string, ScheduleDay>, hour: number) {
  return Object.values(day).filter((entry) =>
    entry.segments.some((segment) => {
      const start = Number(segment.start.slice(0, 2));
      const end = Number(segment.end.slice(0, 2));
      return start <= hour && hour <= end;
    }),
  ).length;
}

function parseDateUtc(date: string) {
  const [year, month, day] = date.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

function formatIsoDateUtc(date: Date) {
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
