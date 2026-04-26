import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  api,
  apiErrorMessage,
  type CoverageResponse,
  type ManagerComments,
  type ManagerSchedules,
  type Period,
  type PeriodStats,
  type PeriodSubmissions,
  type ScheduleBundle,
  type User,
  type UserRole,
} from "../lib/api";
import { datesBetween, dayTypeLabels, formatDate, issueMap, shortDate } from "../lib/schedule";
import { EmptyState, ErrorBanner, StatCard, StatusChip } from "../components/Ui";

type ManagerRoute = "dashboard" | "users" | "periods" | "coverage" | "export";

const roleLabels: Record<UserRole, string> = {
  admin: "Администратор",
  manager: "Менеджер",
  employee: "Сотрудник",
};

export function ManagerDashboard({ route, currentUser }: { route: ManagerRoute; currentUser: User }) {
  const [schedules, setSchedules] = useState<ManagerSchedules | null>(null);
  const [stats, setStats] = useState<PeriodStats | null>(null);
  const [submissions, setSubmissions] = useState<PeriodSubmissions | null>(null);
  const [periods, setPeriods] = useState<Period[]>([]);
  const [activePeriod, setActivePeriod] = useState<Period | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [coverage, setCoverage] = useState<CoverageResponse | null>(null);
  const [selectedDate, setSelectedDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [reviewUserId, setReviewUserId] = useState<number | null>(null);
  const [reviewBundle, setReviewBundle] = useState<ScheduleBundle | null>(null);
  const [reviewComments, setReviewComments] = useState<ManagerComments | null>(null);
  const [reviewText, setReviewText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const isAdmin = currentUser.role === "admin";

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (activePeriod && route === "coverage") {
      const date = selectedDate || activePeriod.periodStart;
      void api.coverage(date, activePeriod.id).then(setCoverage).catch((err) => setError(apiErrorMessage(err)));
    }
  }, [activePeriod, route, selectedDate]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [currentPeriod, historyData, usersData] = await Promise.all([
        api.currentPeriod(),
        api.periodsHistory(),
        api.users(isAdmin ? {} : { role: "employee" }),
      ]);
      const nextActivePeriod = currentPeriod ?? historyData[0] ?? null;
      setActivePeriod(nextActivePeriod);
      setUsers(usersData);
      setPeriods(historyData);

      if (nextActivePeriod) {
        const nextSelectedDate = isDateWithinPeriod(selectedDate, nextActivePeriod) ? selectedDate : nextActivePeriod.periodStart;
        const [scheduleData, coverageData] = await Promise.all([
          api.managerSchedules(nextActivePeriod.id),
          route === "coverage" ? api.coverage(nextSelectedDate, nextActivePeriod.id) : Promise.resolve(null),
        ]);
        setSchedules(scheduleData);
        setSelectedDate(nextSelectedDate);
        if (route === "coverage") {
          setCoverage(coverageData);
        }
        if (currentPeriod) {
          const [statData, submissionsData] = await Promise.all([api.periodStats(), api.periodSubmissions()]);
          setStats(statData);
          setSubmissions(submissionsData);
        } else {
          setStats(null);
          setSubmissions(null);
        }
      } else {
        setSchedules(null);
        setStats(null);
        setSubmissions(null);
        setCoverage(null);
      }
    } catch (err) {
      const message = apiErrorMessage(err);
      if (message.includes("Период не найден")) {
        setError(null);
        setSchedules(null);
        setStats(null);
        setSubmissions(null);
      } else {
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  }

  async function refreshLight() {
    await load();
  }

  async function openReview(userId: number) {
    if (!activePeriod) return;
    setReviewUserId(userId);
    setReviewBundle(null);
    setReviewComments(null);
    setReviewText("");
    setError(null);
    try {
      const [bundle, comments] = await Promise.all([
        api.getScheduleForUser(userId, activePeriod.id),
        api.getManagerComments(userId, activePeriod.id),
      ]);
      setReviewBundle(bundle);
      setReviewComments(comments);
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  async function saveReviewComment(date?: string) {
    if (!reviewUserId || !activePeriod || !reviewText.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const comments = await api.createManagerComment({
        userId: reviewUserId,
        periodId: activePeriod.id,
        date: date ?? null,
        comment: reviewText.trim(),
      });
      setReviewComments(comments);
      setReviewText("");
      await refreshLight();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const rows = schedules?.items ?? [];
  const pending = rows.filter((item) => item.submission.status !== "submitted").length;
  const invalid = rows.filter((item) => !item.validation.isValid).length;
  const coverageMax = useMemo(() => Math.max(1, ...(coverage?.buckets.map((bucket) => bucket.count) ?? [1])), [coverage]);

  if (loading) return <EmptyState title="Загружаем дашборд" text="Получаем сотрудников, статусы и матрицу графиков." />;

  return (
    <>
      <ErrorBanner message={error} />
      {!activePeriod ? <EmptyState title="Нет активного периода" text="Создайте новый период или выберите запись из истории." /> : null}
      {route === "coverage" && activePeriod ? (
        <CoveragePage
          coverage={coverage}
          coverageMax={coverageMax}
          period={activePeriod}
          selectedDate={selectedDate}
          onDateChange={setSelectedDate}
        />
      ) : null}

      {route === "users" ? (
        <UsersPage
          currentUser={currentUser}
          users={users}
          onRefresh={() => void refreshLight().catch((err) => setError(apiErrorMessage(err)))}
          onError={setError}
        />
      ) : null}

      {route === "periods" ? (
        <PeriodsPage
          currentUser={currentUser}
          periods={periods}
          activePeriod={activePeriod}
          stats={stats}
          onRefresh={() => void refreshLight().catch((err) => setError(apiErrorMessage(err)))}
          onError={setError}
        />
      ) : null}

      {route === "export" ? (
        <ExportPage
          periods={periods}
          activePeriod={activePeriod}
          submissions={submissions}
          stats={stats}
          onDownload={downloadExport}
        />
      ) : null}

      {route === "dashboard" && activePeriod ? (
        <DashboardPage
          rows={rows}
          period={activePeriod}
          stats={stats}
          usersCount={users.length}
          pending={pending}
          invalid={invalid}
          onReview={openReview}
        />
      ) : null}

      {reviewUserId ? (
        <ReviewDrawer
          bundle={reviewBundle}
          comments={reviewComments}
          busy={busy}
          text={reviewText}
          onTextChange={setReviewText}
          onSave={saveReviewComment}
          onClose={() => setReviewUserId(null)}
        />
      ) : null}
    </>
  );

  async function downloadExport(periodId: number) {
    setError(null);
    try {
      const response = await api.exportSchedule(periodId);
      if (!response.ok) throw new Error(`Экспорт не удался: ${response.status}`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const period = periods.find((item) => item.id === periodId) ?? activePeriod;
      const link = document.createElement("a");
      link.href = url;
      link.download = `schedule_${period?.periodStart ?? "period"}_${period?.periodEnd ?? "export"}.xlsx`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }
}

function isDateWithinPeriod(date: string, period: Period) {
  return date >= period.periodStart && date <= period.periodEnd;
}

function DashboardPage({
  rows,
  period,
  stats,
  usersCount,
  pending,
  invalid,
  onReview,
}: {
  rows: ManagerSchedules["items"];
  period: Period;
  stats: PeriodStats | null;
  usersCount: number;
  pending: number;
  invalid: number;
  onReview: (userId: number) => void;
}) {
  return (
    <div className="manager-grid">
      <StatCard label="Всего сотрудников" value={stats?.totalEmployees ?? usersCount} />
      <StatCard label="Сдано графиков" value={stats?.submittedCount ?? rows.length - pending} tone="green" />
      <StatCard label="На проверке" value={stats?.pendingCount ?? pending} tone="pink" />

      <section className="panel manager-table-card">
        <div className="panel__head">
          <div>
            <h2>Сотрудники</h2>
            <p>Период {shortDate(period.periodStart)} - {shortDate(period.periodEnd)}</p>
          </div>
          <span className="table-meta">{invalid} с ошибками</span>
        </div>
        <ScheduleTable rows={rows} onReview={onReview} />
      </section>
    </div>
  );
}

function ScheduleTable({ rows, onReview }: { rows: ManagerSchedules["items"]; onReview: (userId: number) => void }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Сотрудник</th>
            <th>Группа</th>
            <th>Статус</th>
            <th>Часы</th>
            <th>Проблемы</th>
            <th>Обновлено</th>
            <th>Действие</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((item) => (
            <tr key={item.user.id}>
              <td>
                <strong>{item.user.full_name}</strong>
                <small>{item.user.email}</small>
              </td>
              <td>{item.user.alliance}</td>
              <td>
                <StatusChip tone={item.submission.status === "submitted" ? "good" : "warn"}>
                  {item.submission.status === "submitted" ? "Сдан" : "Ожидает"}
                </StatusChip>
              </td>
              <td>{item.validation.summary.totalHours}</td>
              <td>{item.validation.issues.length}</td>
              <td>{item.submission.submittedAt ? new Date(item.submission.submittedAt).toLocaleString("ru-RU") : "Черновик"}</td>
              <td>
                <button className="icon-action" type="button" onClick={() => onReview(item.user.id)}>
                  Проверить
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function UsersPage({
  currentUser,
  users,
  onRefresh,
  onError,
}: {
  currentUser: User;
  users: User[];
  onRefresh: () => void;
  onError: (message: string | null) => void;
}) {
  const isAdmin = currentUser.role === "admin";

  async function run(action: () => Promise<unknown>) {
    onError(null);
    try {
      await action();
      onRefresh();
    } catch (err) {
      onError(apiErrorMessage(err));
    }
  }

  return (
    <section className="panel">
      <div className="panel__head">
        <div>
          <h2>Пользователи</h2>
          <p>{isAdmin ? "Полное управление аккаунтами, ролями и группами." : "Сотрудники вашей группы. Изменение ролей доступно администратору."}</p>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ФИО</th>
              <th>Email</th>
              <th>Роль</th>
              <th>Группа</th>
              <th>Верификация</th>
              {isAdmin ? <th>Админ-действия</th> : null}
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <UserRow
                isAdmin={isAdmin}
                key={user.id}
                user={user}
                onVerify={() => run(() => api.verifyUser(user.id))}
                onRole={(role) => run(() => api.changeUserRole(user.id, role))}
                onAlliance={(alliance) => run(() => api.changeUserAlliance(user.id, alliance))}
                onDelete={() => {
                  if (window.confirm(`Удалить пользователя ${user.full_name}?`)) {
                    void run(() => api.deleteUser(user.id));
                  }
                }}
              />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function UserRow({
  user,
  isAdmin,
  onVerify,
  onRole,
  onAlliance,
  onDelete,
}: {
  user: User;
  isAdmin: boolean;
  onVerify: () => void;
  onRole: (role: UserRole) => void;
  onAlliance: (alliance: string) => void;
  onDelete: () => void;
}) {
  const [alliance, setAlliance] = useState(user.alliance);

  return (
    <tr>
      <td>{user.full_name}</td>
      <td>{user.email}</td>
      <td>
        {isAdmin ? (
          <select value={user.role} onChange={(event) => onRole(event.target.value as UserRole)}>
            {Object.entries(roleLabels).map(([role, label]) => (
              <option key={role} value={role}>{label}</option>
            ))}
          </select>
        ) : (
          roleLabels[user.role]
        )}
      </td>
      <td>
        {isAdmin ? (
          <div className="inline-edit">
            <input value={alliance} onChange={(event) => setAlliance(event.target.value)} />
            <button className="icon-action" type="button" onClick={() => onAlliance(alliance)}>
              OK
            </button>
          </div>
        ) : (
          user.alliance
        )}
      </td>
      <td>
        <StatusChip tone={user.isVerified ? "good" : "warn"}>{user.isVerified ? "Подтвержден" : "Ожидает"}</StatusChip>
      </td>
      {isAdmin ? (
        <td>
          <div className="admin-actions">
            <button className="icon-action" disabled={user.isVerified} type="button" onClick={onVerify}>
              Верифицировать
            </button>
            <button className="icon-action icon-action--danger" type="button" onClick={onDelete}>
              Удалить
            </button>
          </div>
        </td>
      ) : null}
    </tr>
  );
}

function PeriodsPage({
  currentUser,
  periods,
  activePeriod,
  stats,
  onRefresh,
  onError,
}: {
  currentUser: User;
  periods: Period[];
  activePeriod: Period | null;
  stats: PeriodStats | null;
  onRefresh: () => void;
  onError: (message: string | null) => void;
}) {
  const seedPeriod = activePeriod ?? periods[0] ?? null;
  const [form, setForm] = useState({
    name: "Новый период",
    alliance: currentUser.alliance,
    periodStart: seedPeriod?.periodStart ?? new Date().toISOString().slice(0, 10),
    periodEnd: seedPeriod?.periodEnd ?? new Date().toISOString().slice(0, 10),
    deadline: seedPeriod?.deadline.slice(0, 16) ?? new Date().toISOString().slice(0, 16),
  });

  useEffect(() => {
    const nextSeed = activePeriod ?? periods[0] ?? null;
    if (!nextSeed) return;
    setForm((state) => ({
      ...state,
      alliance: currentUser.alliance,
      periodStart: nextSeed.periodStart,
      periodEnd: nextSeed.periodEnd,
      deadline: nextSeed.deadline.slice(0, 16),
    }));
  }, [activePeriod?.id, periods, currentUser.alliance]);

  async function createPeriod(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onError(null);
    try {
      await api.createPeriod({
        name: form.name,
        alliance: currentUser.role === "admin" ? form.alliance : undefined,
        periodStart: form.periodStart,
        periodEnd: form.periodEnd,
        deadline: new Date(form.deadline).toISOString(),
      });
      onRefresh();
    } catch (err) {
      onError(apiErrorMessage(err));
    }
  }

  async function closePeriod(periodId: number) {
    onError(null);
    try {
      await api.closePeriod(periodId);
      onRefresh();
    } catch (err) {
      onError(apiErrorMessage(err));
    }
  }

  return (
    <div className="admin-grid periods-grid">
      <div className="periods-stack">
        <section className="panel period-overview">
          <div className="panel__head">
            <div>
              <h2>Периоды сбора</h2>
              <p>{currentUser.role === "admin" ? "Администратор управляет периодами всех групп." : "Менеджер управляет периодами только своей группы."}</p>
            </div>
            <StatusChip tone={seedPeriod?.isOpen ? "good" : "neutral"}>{seedPeriod?.isOpen ? "Открыт" : "Нет периода"}</StatusChip>
          </div>
          <div className="period-kpi">
            <span>{seedPeriod?.name ?? "Нет периода"}</span>
            <strong>{seedPeriod ? `${shortDate(seedPeriod.periodStart)} - ${shortDate(seedPeriod.periodEnd)}` : "—"}</strong>
            <small>
              {seedPeriod ? `Сдано ${stats?.submittedCount ?? 0} из ${stats?.totalEmployees ?? 0}. Дедлайн: ${new Date(seedPeriod.deadline).toLocaleString("ru-RU")}` : "Создайте новый период или выберите запись из истории."}
            </small>
          </div>
        </section>

        <section className="panel admin-wide">
          <div className="panel__head">
            <div>
              <h2>История</h2>
              <p>Плотная таблица вместо одиночной карточки: так проще сверять периоды.</p>
            </div>
          </div>
          <PeriodTable periods={periods} onClose={closePeriod} />
        </section>
      </div>

      <form className="panel admin-form admin-form--periods" onSubmit={createPeriod}>
        <h2>Создать период</h2>
        <div className="period-form-grid">
          <label className="period-field period-field--full">
            Название
            <input value={form.name} onChange={(event) => setForm((state) => ({ ...state, name: event.target.value }))} placeholder="Новый период" />
          </label>
          {currentUser.role === "admin" ? (
            <label className="period-field period-field--full">
              Группа
              <input value={form.alliance} onChange={(event) => setForm((state) => ({ ...state, alliance: event.target.value }))} placeholder="Retail East" />
            </label>
          ) : null}
          <label className="period-field">
            Старт
            <input type="date" value={form.periodStart} onChange={(event) => setForm((state) => ({ ...state, periodStart: event.target.value }))} />
          </label>
          <label className="period-field">
            Финиш
            <input type="date" value={form.periodEnd} onChange={(event) => setForm((state) => ({ ...state, periodEnd: event.target.value }))} />
          </label>
          <label className="period-field period-field--full">
            Дедлайн
            <input type="datetime-local" value={form.deadline} onChange={(event) => setForm((state) => ({ ...state, deadline: event.target.value }))} />
          </label>
        </div>
        <button className="button button--primary button--compact period-submit" type="submit">Открыть сбор</button>
      </form>
    </div>
  );
}

function PeriodTable({ periods, onClose }: { periods: Period[]; onClose: (periodId: number) => void }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Период</th>
            <th>Группа</th>
            <th>Даты</th>
            <th>Дедлайн</th>
            <th>Статус</th>
            <th>Действие</th>
          </tr>
        </thead>
        <tbody>
          {periods.map((period) => (
            <tr key={period.id}>
              <td><strong>{period.name}</strong></td>
              <td>{period.alliance}</td>
              <td>{shortDate(period.periodStart)} - {shortDate(period.periodEnd)}</td>
              <td>{new Date(period.deadline).toLocaleString("ru-RU")}</td>
              <td><StatusChip tone={period.isOpen ? "good" : "neutral"}>{period.isOpen ? "Открыт" : "Закрыт"}</StatusChip></td>
              <td>
                <button className="icon-action" disabled={!period.isOpen} type="button" onClick={() => onClose(period.id)}>
                  Закрыть
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ExportPage({
  periods,
  activePeriod,
  submissions,
  stats,
  onDownload,
}: {
  periods: Period[];
  activePeriod: Period | null;
  submissions: PeriodSubmissions | null;
  stats: PeriodStats | null;
  onDownload: (periodId: number) => void;
}) {
  const list = periods.length ? periods : activePeriod ? [activePeriod] : [];

  return (
    <div className="admin-grid export-grid">
      <StatCard label="Сдано" value={stats?.submittedCount ?? submissions?.submitted.length ?? 0} tone="green" />
      <StatCard label="Ожидает" value={stats?.pendingCount ?? submissions?.pending.length ?? 0} tone="pink" />
      <section className="panel admin-wide">
        <div className="panel__head">
          <div>
            <h2>Экспорт</h2>
            <p>Excel выгружается по выбранному периоду. Администратор получает любую группу, менеджер - только свою область доступа.</p>
          </div>
          <button className="button button--primary" disabled={!activePeriod} type="button" onClick={() => activePeriod && onDownload(activePeriod.id)}>Активный период</button>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Период</th>
                <th>Группа</th>
                <th>Даты</th>
                <th>Статус</th>
                <th>Файл</th>
              </tr>
            </thead>
            <tbody>
              {list.map((period) => (
                <tr key={period.id}>
                  <td><strong>{period.name}</strong></td>
                  <td>{period.alliance}</td>
                  <td>{shortDate(period.periodStart)} - {shortDate(period.periodEnd)}</td>
                  <td><StatusChip tone={period.isOpen ? "good" : "neutral"}>{period.isOpen ? "Открыт" : "Закрыт"}</StatusChip></td>
                  <td>
                    <button className="icon-action" type="button" onClick={() => onDownload(period.id)}>
                      Скачать XLSX
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function CoveragePage({
  coverage,
  coverageMax,
  period,
  selectedDate,
  onDateChange,
}: {
  coverage: CoverageResponse | null;
  coverageMax: number;
  period: Period;
  selectedDate: string;
  onDateChange: (date: string) => void;
}) {
  return (
    <section className="panel coverage-page">
      <div className="panel__head">
        <div>
          <h2>Покрытие</h2>
          <p>{period.name}</p>
        </div>
        <input type="date" value={selectedDate} onChange={(event) => onDateChange(event.target.value)} />
      </div>
      <div className="coverage-legend" aria-label="Легенда покрытия">
        <span><i className="coverage-legend__fill" /> Покрытие</span>
        <span><i className="coverage-legend__fill coverage-legend__fill--deficit" /> Дефицит</span>
      </div>
      <div className="coverage-chart">
        {coverage?.buckets.map((bucket) => (
          <div className="coverage-row" key={bucket.hour} title={bucket.users.length ? bucket.users.join(", ") : "Нет сотрудников"}>
            <span>{bucket.hour}</span>
            <div>
              <b style={{ width: `${(bucket.count / coverageMax) * 100}%` }} />
            </div>
            <strong>{bucket.count}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

function ReviewDrawer({
  bundle,
  comments,
  text,
  busy,
  onTextChange,
  onSave,
  onClose,
}: {
  bundle: ScheduleBundle | null;
  comments: ManagerComments | null;
  text: string;
  busy: boolean;
  onTextChange: (value: string) => void;
  onSave: (date?: string) => void;
  onClose: () => void;
}) {
  const issuesByDate = issueMap(bundle?.validation.issues ?? []);

  return (
    <aside className="review-drawer">
      <div className="review-drawer__head">
        <div>
          <span className="eyebrow">Проверка графика</span>
          <h2>{bundle?.user.full_name ?? "Загрузка"}</h2>
        </div>
        <button className="icon-action" type="button" onClick={onClose}>Закрыть</button>
      </div>

      {!bundle ? <EmptyState title="Загрузка" text="Получаем график сотрудника и комментарии." /> : (
        <>
          <div className="review-summary">
            <StatusChip tone={bundle.submission.status === "submitted" ? "good" : "warn"}>
              {bundle.submission.status === "submitted" ? "Сдан" : "Черновик"}
            </StatusChip>
            <strong>{bundle.validation.summary.totalHours} часов</strong>
            <span>{shortDate(bundle.period.periodStart)} - {shortDate(bundle.period.periodEnd)}</span>
          </div>

          <div className="review-grid">
            {datesBetween(bundle.period.periodStart, bundle.period.periodEnd).map((date) => {
              const day = bundle.entries[date];
              const issues = issuesByDate[date] ?? [];
              const managerComment = comments?.dayComments[date] ?? day?.managerComment;
              return (
                <article className={issues.length ? "review-day review-day--issue" : "review-day"} key={date}>
                  <header>
                    <strong>{formatDate(date)}</strong>
                    <StatusChip tone={day?.dayType === "work" ? "good" : "neutral"}>{dayTypeLabels[day?.dayType ?? "unavailable"]}</StatusChip>
                  </header>
                  <p>{day?.segments.length ? day.segments.map((segment) => `${segment.start}-${segment.end}`).join(", ") : "Без смен"}</p>
                  {day?.employeeComment ? <small>Комментарий сотрудника: {day.employeeComment}</small> : null}
                  {managerComment ? <small>Комментарий менеджера: {managerComment}</small> : null}
                  {issues.map((issue) => <small className="review-issue" key={`${issue.code}-${issue.message}`}>{issue.message}</small>)}
                  <button className="icon-action" type="button" disabled={!text.trim() || busy} onClick={() => onSave(date)}>
                    Комментировать день
                  </button>
                </article>
              );
            })}
          </div>

          <textarea
            className="comment-box"
            value={text}
            onChange={(event) => onTextChange(event.target.value)}
            placeholder="Комментарий менеджера к графику или выбранному дню"
          />
          <div className="review-actions">
            <button className="button button--primary" type="button" disabled={!text.trim() || busy} onClick={() => onSave()}>
              Сохранить комментарий
            </button>
          </div>

          <section className="comment-history">
            <h3>История комментариев</h3>
            {comments?.scheduleComment ? (
              <article>
                <strong>Весь график</strong>
                <p>{comments.scheduleComment}</p>
              </article>
            ) : null}
            {comments
              ? Object.entries(comments.dayComments).map(([date, comment]) => (
                <article key={date}>
                  <strong>{formatDate(date)}</strong>
                  <p>{comment}</p>
                </article>
              ))
              : null}
            {!comments?.scheduleComment && !Object.keys(comments?.dayComments ?? {}).length ? <p className="muted">Комментариев пока нет.</p> : null}
          </section>
        </>
      )}
    </aside>
  );
}
