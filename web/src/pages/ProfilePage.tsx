import type { User } from "../lib/api";
import { StatusChip } from "../components/Ui";

export function ProfilePage({ user }: { user: User }) {
  return (
    <section className="panel profile-card">
      <h2>Профиль</h2>
      <dl>
        <dt>ФИО</dt>
        <dd>{user.full_name}</dd>
        <dt>Почта</dt>
        <dd>{user.email}</dd>
        <dt>Группа</dt>
        <dd>{user.alliance}</dd>
        <dt>Роль</dt>
        <dd>{user.role}</dd>
        <dt>Норма часов</dt>
        <dd>{user.weeklyNormHours ?? "Не задана"}</dd>
        <dt>Статус</dt>
        <dd>
          <StatusChip tone={user.isVerified ? "good" : "warn"}>{user.isVerified ? "Подтвержден" : "Ожидает подтверждения"}</StatusChip>
        </dd>
      </dl>
    </section>
  );
}
