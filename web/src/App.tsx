import { useEffect, useState } from "react";
import { AppLayout, type AppRoute } from "./components/Layout";
import { EmptyState } from "./components/Ui";
import { api, apiErrorMessage, clearToken, getToken, type User } from "./lib/api";
import { AuthPage } from "./pages/AuthPage";
import { EmployeeSchedule } from "./pages/EmployeeSchedule";
import { ManagerDashboard } from "./pages/ManagerDashboard";
import { ProfilePage } from "./pages/ProfilePage";
import { VerifyPage } from "./pages/VerifyPage";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [route, setRoute] = useState<AppRoute>("schedule");
  const [booting, setBooting] = useState(true);
  const [bootError, setBootError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      setBooting(false);
      return;
    }
    api
      .me()
      .then((currentUser) => {
        setUser(currentUser);
        setRoute(defaultRoute(currentUser));
      })
      .catch((err) => {
        setBootError(apiErrorMessage(err));
        clearToken();
      })
      .finally(() => setBooting(false));
  }, []);

  if (booting) {
    return <EmptyState title="Запуск" text="Проверяем сессию и подключение к API." />;
  }

  if (!user) {
    return <AuthPage onAuth={(nextUser) => {
      setUser(nextUser);
      setRoute(defaultRoute(nextUser));
      setBootError(null);
    }} />;
  }

  if (!user.isVerified) {
    return (
      <VerifyPage
        onVerified={(nextUser) => {
          setUser(nextUser);
          setRoute(defaultRoute(nextUser));
        }}
      />
    );
  }

  return (
    <AppLayout
      user={user}
      route={route}
      onRouteChange={setRoute}
      onLogout={() => {
        clearToken();
        setUser(null);
      }}
    >
      {bootError ? <div className="error-banner">{bootError}</div> : null}
      {renderRoute(user, route)}
    </AppLayout>
  );
}

function defaultRoute(user: User): AppRoute {
  return user.role === "employee" ? "schedule" : "dashboard";
}

function renderRoute(user: User, route: AppRoute) {
  if (user.role === "employee") {
    return route === "profile" ? <ProfilePage user={user} /> : <EmployeeSchedule />;
  }

  if (route === "profile") return <ProfilePage user={user} />;
  return <ManagerDashboard currentUser={user} route={route === "schedule" || route === "verify" ? "dashboard" : route} />;
}
