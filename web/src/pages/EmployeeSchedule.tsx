import { useEffect, useMemo, useState } from "react";
import { api, apiErrorMessage, type DayType, type ScheduleBundle, type ScheduleDay, type TimeSegment } from "../lib/api";
import { datesBetween, dayTypeLabels, defaultWorkDay, formatDate, issueMap, normalizeDay } from "../lib/schedule";
import { EmptyState, ErrorBanner, StatusChip } from "../components/Ui";

export function EmployeeSchedule() {
  const [bundle, setBundle] = useState<ScheduleBundle | null>(null);
  const [days, setDays] = useState<Record<string, ScheduleDay>>({});
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMySchedule();
      setBundle(data);
      setDays(data.entries);
      setComment(data.submission.employeeComment ?? "");
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const data = await api.saveMySchedule(days, comment || null);
      setBundle(data);
      setDays(data.entries);
      setComment(data.submission.employeeComment ?? "");
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function submit() {
    setSaving(true);
    setError(null);
    try {
      await api.saveMySchedule(days, comment || null);
      const data = await api.submitMySchedule();
      setBundle(data);
      setDays(data.entries);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  const periodDays = useMemo(() => {
    if (!bundle) return [];
    return datesBetween(bundle.period.periodStart, bundle.period.periodEnd);
  }, [bundle]);

  const issuesByDate = useMemo(() => issueMap(bundle?.validation.issues ?? []), [bundle]);

  if (loading) return <EmptyState title="Загружаем график" text="Получаем активный период и валидацию." />;
  if (!bundle) return <ErrorBanner message={error ?? "Активный график не найден"} />;

  const total = bundle.validation.summary.totalHours;
  const norm = bundle.user.weeklyNormHours ?? 40;
  const isSubmitted = bundle.submission.status === "submitted";

  return (
    <div className="employee-grid">
      <section className="panel schedule-editor">
        <div className="panel__head">
          <div>
            <h2>Редактор графика</h2>
            <p>Период: {bundle.period.periodStart} — {bundle.period.periodEnd}</p>
          </div>
          <button className="button button--ghost" onClick={copyWeek} type="button">
            Копировать неделю
          </button>
        </div>
        <ErrorBanner message={error} />
        <div className="day-list">
          {periodDays.map((date) => (
            <DayRow
              key={date}
              date={date}
              value={normalizeDay(days[date])}
              issues={issuesByDate[date] ?? []}
              onChange={(next) => setDays((current) => ({ ...current, [date]: next }))}
            />
          ))}
        </div>
        <textarea
          className="comment-box"
          placeholder="Комментарий к графику"
          value={comment}
          onChange={(event) => setComment(event.target.value)}
        />
      </section>

      <aside className="summary-stack">
        <section className="panel summary-card">
          <h2>Сводка</h2>
          <strong className="stencil">{total}/{norm}</strong>
          <p>Часы за период</p>
          <div className="summary-line">
            <span>Статус</span>
            <StatusChip tone={isSubmitted ? "good" : "warn"}>{isSubmitted ? "Отправлен" : "Черновик"}</StatusChip>
          </div>
          <div className="summary-line">
            <span>Ошибки</span>
            <b>{bundle.validation.issues.filter((issue) => issue.severity === "error").length}</b>
          </div>
          <div className="summary-line">
            <span>Предупреждения</span>
            <b>{bundle.validation.issues.filter((issue) => issue.severity === "warning").length}</b>
          </div>
        </section>
        {issuesByDate._global?.length ? (
          <section className="panel issue-card">
            <h3>Общие замечания</h3>
            {issuesByDate._global.map((issue) => (
              <p key={`${issue.code}-${issue.message}`}>{issue.message}</p>
            ))}
          </section>
        ) : null}
        <div className="action-row">
          <button className="button button--ghost" disabled={saving} onClick={save} type="button">
            {saving ? "Сохраняем..." : "Сохранить"}
          </button>
          <button className="button button--primary" disabled={saving} onClick={submit} type="button">
            Отправить
          </button>
        </div>
      </aside>
    </div>
  );

  function copyWeek() {
    const firstWork = periodDays.find((date) => days[date]?.dayType === "work");
    if (!firstWork) return;
    const template = normalizeDay(days[firstWork]);
    setDays((current) => {
      const next = { ...current };
      periodDays.forEach((date) => {
        const day = new Date(`${date}T00:00:00`).getDay();
        if (day !== 0 && day !== 6) {
          next[date] = { ...template, segments: template.segments.map((segment) => ({ ...segment })) };
        }
      });
      return next;
    });
  }
}

function DayRow({
  date,
  value,
  issues,
  onChange,
}: {
  date: string;
  value: ScheduleDay;
  issues: { severity: string; message: string; code: string }[];
  onChange: (value: ScheduleDay) => void;
}) {
  const hasIssue = issues.length > 0;
  const dayType = value.dayType ?? "unavailable";
  const segments = value.segments.length ? value.segments : [{ start: "09:00", end: "18:00" }];

  function setDayType(next: DayType) {
    onChange(next === "work" ? { ...defaultWorkDay(), employeeComment: value.employeeComment } : { ...value, dayType: next, status: next, segments: [] });
  }

  function updateSegment(index: number, segment: TimeSegment) {
    const next = [...segments];
    next[index] = segment;
    onChange({ ...value, dayType: "work", status: "work", segments: next });
  }

  return (
    <article className={hasIssue ? "day-row day-row--issue" : "day-row"}>
      <div className="day-row__title">
        <strong>{formatDate(date)}</strong>
        <select value={dayType} onChange={(event) => setDayType(event.target.value as DayType)}>
          {Object.entries(dayTypeLabels).map(([key, label]) => (
            <option value={key} key={key}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div className="segment-list">
        {dayType === "work" ? (
          segments.map((segment, index) => (
            <div className="time-segment" key={index}>
              <input
                inputMode="numeric"
                pattern="[0-2][0-9]:[0-5][0-9]"
                placeholder="09:00"
                value={segment.start}
                onChange={(event) => updateSegment(index, { ...segment, start: event.target.value })}
              />
              <span>—</span>
              <input
                inputMode="numeric"
                pattern="[0-2][0-9]:[0-5][0-9]"
                placeholder="18:00"
                value={segment.end}
                onChange={(event) => updateSegment(index, { ...segment, end: event.target.value })}
              />
            </div>
          ))
        ) : (
          <span className="muted">Интервалы не нужны</span>
        )}
      </div>

      {hasIssue ? (
        <div className="day-row__issues">
          {issues.map((issue) => (
            <span key={issue.code}>{issue.message}</span>
          ))}
        </div>
      ) : null}
    </article>
  );
}
