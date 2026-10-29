export function readPasswordResetToken(location) {
  return new URLSearchParams(location.hash.slice(1)).get("token");
}
