export type UserRole = "admin" | "manager" | "employee";
export type DayType = "work" | "day_off" | "vacation" | "holiday" | "unavailable";
export type SubmissionStatus = "draft" | "submitted";
export type IssueSeverity = "error" | "warning";

export interface User {
  id: number;
  email: string;
  full_name: string;
  external_id?: string | null;
  alliance: string;
  role: UserRole;
  registered: boolean;
  isVerified: boolean;
  employeeCategory: "adult" | "minor_student" | "minor_not_student";
  weeklyNormHours?: number | null;
}

export interface Period {
  id: number;
  name: string;
  alliance: string;
  periodStart: string;
  periodEnd: string;
  deadline: string;
  isOpen: boolean;
  holidays: Record<string, string>;
  createdAt: string;
  updatedAt: string;
}

export interface TimeSegment {
  start: string;
  end: string;
}

export interface ScheduleDay {
  status?: string | null;
  dayType?: DayType | null;
  segments: TimeSegment[];
  employeeComment?: string | null;
  managerComment?: string | null;
  meta?: Record<string, unknown> | null;
}

export interface ValidationIssue {
  severity: IssueSeverity;
  code: string;
  date: string | null;
  message: string;
}

export interface ValidationResponse {
  isValid: boolean;
  summary: {
    totalHours: number;
    weeklyHours: Record<string, number>;
    daysOffCount: Record<string, number>;
  };
  issues: ValidationIssue[];
}

export interface Submission {
  id: number;
  status: SubmissionStatus;
  submittedAt: string | null;
  employeeComment: string | null;
  managerComment: string | null;
  periodId: number;
  userId: number;
}

export interface ScheduleBundle {
  user: User;
  period: Period;
  submission: Submission;
  entries: Record<string, ScheduleDay>;
  validation: ValidationResponse;
}

export interface ManagerScheduleItem {
  user: User;
  submission: Submission;
  entries: Record<string, ScheduleDay>;
  validation: ValidationResponse;
}

export interface ManagerSchedules {
  period: Period;
  items: ManagerScheduleItem[];
}

export interface CoverageBucket {
  hour: string;
  count: number;
  users: string[];
}

export interface CoverageResponse {
  day: string;
  periodId: number;
  buckets: CoverageBucket[];
}

export interface PeriodStats {
  totalEmployees: number;
  submittedCount: number;
  pendingCount: number;
}

export interface PeriodSubmissions {
  submitted: Array<{ id: number; fullName: string; email: string; group: string; status: string }>;
  pending: Array<{ id: number; fullName: string; email: string; group: string; status: string }>;
}

export interface ManagerComments {
  userId: number;
  periodId: number;
  scheduleComment: string | null;
  dayComments: Record<string, string>;
}

export interface ScheduleTemplate {
  id: number;
  userId: number;
  name: string;
  workDays: number;
  restDays: number;
  shiftStart: string;
  shiftEnd: string;
  hasBreak: boolean;
  breakStart?: string | null;
  breakEnd?: string | null;
  createdAt: string;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `API request failed with ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://144.31.181.170:8000";
const TOKEN_KEY = "t2_schedule_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();

  if (!(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let detail: unknown = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.detail ?? payload;
    } catch {
      detail = await response.text();
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  baseUrl: API_BASE_URL,

  async login(email: string, password: string) {
    const token = await request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(token.access_token);
    return token;
  },

  register(payload: {
    full_name: string;
    email: string;
    password: string;
    alliance: string;
    employeeCategory: User["employeeCategory"];
  }) {
    return request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  verify(token: string) {
    return request<User>("/auth/verify", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
  },

  me() {
    return request<User>("/auth/me");
  },

  getMySchedule() {
    return request<ScheduleBundle>("/schedules/me");
  },

  saveMySchedule(days: Record<string, ScheduleDay>, employeeComment?: string | null) {
    return request<ScheduleBundle>("/schedules/me", {
      method: "PUT",
      body: JSON.stringify({ days, employeeComment }),
    });
  },

  submitMySchedule() {
    return request<ScheduleBundle>("/schedules/me/submit", {
      method: "POST",
    });
  },

  validateSchedule(periodId: number, days: Record<string, ScheduleDay>) {
    return request<ValidationResponse>("/schedules/validate", {
      method: "POST",
      body: JSON.stringify({ periodId, days }),
    });
  },

  templates() {
    return request<ScheduleTemplate[]>("/templates");
  },

  currentPeriod() {
    return request<Period | null>("/periods/current");
  },

  periodsHistory() {
    return request<Period[]>("/periods/history");
  },

  createPeriod(payload: {
    name: string;
    alliance?: string | null;
    periodStart: string;
    periodEnd: string;
    deadline: string;
  }) {
    return request<Period>("/periods", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  closePeriod(periodId: number) {
    return request<Period>(`/periods/${periodId}/close`, {
      method: "POST",
    });
  },

  periodStats() {
    return request<PeriodStats>("/periods/current/stats");
  },

  periodSubmissions() {
    return request<PeriodSubmissions>("/periods/current/submissions");
  },

  managerSchedules(periodId?: number) {
    const query = periodId ? `?period_id=${periodId}` : "";
    return request<ManagerSchedules>(`/manager/schedules${query}`);
  },

  getScheduleForUser(userId: number, periodId?: number) {
    const query = periodId ? `?period_id=${periodId}` : "";
    return request<ScheduleBundle>(`/schedules/by-user/${userId}${query}`);
  },

  getManagerComments(userId: number, periodId: number) {
    const params = new URLSearchParams({ user_id: String(userId), period_id: String(periodId) });
    return request<ManagerComments>(`/manager/comments?${params.toString()}`);
  },

  createManagerComment(payload: { userId: number; periodId: number; date?: string | null; comment: string }) {
    return request<ManagerComments>("/manager/comments", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  coverage(day: string, periodId?: number) {
    const params = new URLSearchParams({ day });
    if (periodId) {
      params.set("period_id", String(periodId));
    }
    return request<CoverageResponse>(`/manager/coverage?${params.toString()}`);
  },

  users(params: { verified?: boolean; alliance?: string; role?: UserRole } = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        query.set(key, String(value));
      }
    });
    const suffix = query.size ? `?${query.toString()}` : "";
    return request<User[]>(`/admin/users${suffix}`);
  },

  verifyUser(userId: number) {
    return request<User>(`/admin/users/${userId}/verify`, {
      method: "PUT",
    });
  },

  changeUserRole(userId: number, role: UserRole) {
    return request<User>(`/admin/users/${userId}/role`, {
      method: "PUT",
      body: JSON.stringify({ role }),
    });
  },

  changeUserAlliance(userId: number, alliance: string) {
    return request<User>(`/admin/users/${userId}/alliance`, {
      method: "PUT",
      body: JSON.stringify({ alliance }),
    });
  },

  deleteUser(userId: number) {
    return request<void>(`/admin/users/${userId}`, {
      method: "DELETE",
    });
  },

  exportSchedule(periodId?: number) {
    const query = periodId ? `?period_id=${periodId}` : "";
    return fetch(`${API_BASE_URL}/export/schedule${query}`, {
      headers: getToken() ? { Authorization: `Bearer ${getToken()}` } : undefined,
    });
  },
};

export function apiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === "string") {
      return error.detail;
    }
    if (typeof error.detail === "object" && error.detail && "message" in error.detail) {
      return String((error.detail as { message: unknown }).message);
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Не удалось выполнить запрос";
}
