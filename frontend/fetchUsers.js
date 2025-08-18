let usersMap = {}; 

async function fetchUsers() {
    const res = await fetch('/users/');
    if (!res.ok) throw new Error("Failed to fetch users");
    const users = await res.json();
    usersMap = {};
    users.forEach(user => {
        usersMap[user.id] = user.username;
    });
    return users; 
}
