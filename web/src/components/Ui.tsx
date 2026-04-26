import type { ReactNode } from "react";

export function StatCard({
  label,
  value,
  tone = "dark",
  compact = false,
  children,
}: {
  label: string;
  value: ReactNode;
  tone?: "dark" | "green" | "pink";
  compact?: boolean;
  children?: ReactNode;
}) {
  return (
    <article className={`stat-card stat-card--${tone}${compact ? " stat-card--compact" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {children}
    </article>
  );
}

export function StatusChip({ children, tone = "neutral" }: { children: ReactNode; tone?: "good" | "warn" | "neutral" }) {
  return <span className={`status-chip status-chip--${tone}`}>{children}</span>;
}

export function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      <p>{text}</p>
    </div>
  );
}

export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null;
  return <div className="error-banner">{message}</div>;
}
