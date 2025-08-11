export async function fetchUsers(authHeaders = null) {
  const options = {};
  if (authHeaders) {
    options.headers = authHeaders;
  }

  const res = await fetch('/users/', options);
  if (!res.ok) throw new Error('Failed to fetch users');
  const users = await res.json();
  return users;
}
