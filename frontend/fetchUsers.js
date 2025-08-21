let usersMap = {};

async function fetchUsers() {
    try {
        const res = await fetch('/users/', {
            method: 'GET',
            credentials: 'include' 
        });

        if (!res.ok) throw new Error("Failed to fetch users");

        const users = await res.json();
        usersMap = {};
        users.forEach(user => { usersMap[user.id] = user.username; });
        return users;

    } catch (error) {
        console.error("Error fetching users:", error);
        return [];
    }
}
