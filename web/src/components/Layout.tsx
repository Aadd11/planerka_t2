import type { ReactNode } from "react";
import type { User } from "../lib/api";
import { T2Logo } from "./Brand";

export type AppRoute =
  | "schedule"
  | "profile"
  | "dashboard"
  | "users"
  | "periods"
  | "coverage"
  | "export"
  | "verify";

interface LayoutProps {
  user: User;
  route: AppRoute;
  onRouteChange: (route: AppRoute) => void;
  onLogout: () => void;
  children: ReactNode;
}

const icons: Record<string, string> = {
  schedule: "▦",
  profile: "◎",
  dashboard: "▣",
  users: "♙",
  periods: "◴",
  coverage: "▥",
  export: "⇩",
};

export function AppLayout({ user, route, onRouteChange, onLogout, children }: LayoutProps) {
  const isEmployee = user.role === "employee";
  const nav = isEmployee
    ? [
        ["schedule", "График"],
        ["profile", "Профиль"],
      ]
    : user.role === "manager"
      ? [
          ["dashboard", "Проверка"],
          ["users", "Команда"],
          ["periods", "Периоды"],
          ["coverage", "Покрытие"],
          ["export", "Экспорт"],
        ]
    : [
        ["dashboard", "Дашборд"],
        ["users", "Пользователи"],
        ["periods", "Периоды сбора"],
        ["coverage", "Покрытие"],
        ["export", "Экспорт"],
      ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <T2Logo />
        <nav className="sidebar__nav">
          {nav.map(([key, label]) => (
            <button
              className={route === key ? "nav-item nav-item--active" : "nav-item"}
              key={key}
              onClick={() => onRouteChange(key as AppRoute)}
              type="button"
            >
              <span>{icons[key]}</span>
              {label}
            </button>
          ))}
        </nav>
        <button className="nav-item nav-item--logout" onClick={onLogout} type="button">
          <span>↪</span>
          Выйти
        </button>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">{user.alliance}</p>
            <h1>{isEmployee ? "График работы" : user.role === "admin" ? "Администрирование графиков" : "Контроль группы"}</h1>
          </div>
          <div className="user-pill">
            <span className="user-pill__avatar">{initials(user.full_name)}</span>
            <span>
              <strong>{user.full_name}</strong>
              <small>{roleLabel(user.role)}</small>
            </span>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}

function initials(name: string) {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function roleLabel(role: User["role"]) {
  if (role === "admin") return "Администратор";
  if (role === "manager") return "Менеджер";
  return "Сотрудник";
}
