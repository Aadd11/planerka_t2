import type { User } from "../lib/api";
import { StatusChip } from "../components/Ui";

export function ProfilePage({ user }: { user: User }) {
  const roleLabel = user.role === "admin" ? "Администратор" : user.role === "manager" ? "Менеджер" : "Сотрудник";
  const categoryLabel = user.employeeCategory === "adult" ? "Взрослый" : user.employeeCategory === "minor_student" ? "Несовершеннолетний студент" : "Несовершеннолетний";

  return (
    <section className="panel profile-card">
      <div className="profile-card__head">
        <div>
          <p className="eyebrow">{user.alliance}</p>
          <h2>{user.full_name}</h2>
          <span>{user.email}</span>
        </div>
        <StatusChip tone={user.isVerified ? "good" : "warn"}>{user.isVerified ? "Подтвержден" : "Ожидает подтверждения"}</StatusChip>
      </div>

      <dl className="profile-list">
        <div>
          <dt>Роль</dt>
          <dd>{roleLabel}</dd>
        </div>
        <div>
          <dt>Норма часов</dt>
          <dd>{user.weeklyNormHours ?? "Не задана"}</dd>
        </div>
        <div>
          <dt>Категория</dt>
          <dd>{categoryLabel}</dd>
        </div>
        <div>
          <dt>Группа</dt>
          <dd>{user.alliance}</dd>
        </div>
        <div>
          <dt>Внешний ID</dt>
          <dd>{user.external_id ?? "Не задан"}</dd>
        </div>
      </dl>
    </section>
  );
}
