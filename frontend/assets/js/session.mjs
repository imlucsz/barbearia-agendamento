export function expireSessionOnUnauthorized(status, auth, storage, location) {
  if (!auth || status !== 401) return false;

  storage.removeItem("token");
  storage.removeItem("user");

  const currentPage = `${location.pathname.split("/").pop()}${location.search}`;
  location.href = `login.html?redirect=${encodeURIComponent(currentPage)}`;
  return true;
}
