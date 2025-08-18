let usersMap = {};

async function fetchUsers() {
    const token = localStorage.getItem("access_token");
    const res = await fetch('/users/', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) throw new Error("Failed to fetch users");
    const users = await res.json();
    usersMap = {};
    users.forEach(user => { usersMap[user.id] = user.username; });
    return users;
}
