export function shouldRefreshSession(status, auth, endpoint) {
  return status === 401 && auth && endpoint !== "/auth/refresh" && endpoint !== "/auth/logout";
}

export function expireSessionOnUnauthorized(status, auth, storage, location, responseText = "") {
  let blocked = false;
  if (status === 403) {
    try {
      blocked = JSON.parse(responseText).detail === "Conta bloqueada";
    } catch {
      blocked = false;
    }
  }
  if (!auth || (status !== 401 && !blocked)) return false;

  storage.removeItem("token");
  storage.removeItem("user");

  const currentPage = `${location.pathname.split("/").pop()}${location.search}`;
  location.href = `login.html?redirect=${encodeURIComponent(currentPage)}`;
  return true;
}
