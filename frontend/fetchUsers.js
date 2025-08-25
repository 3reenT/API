async function fetchUsers() {
    try {
        const res = await fetch('/users/', { credentials: 'include' });
        if (res.status === 401) {
            alert("You must login first");
            window.location.href = "/";
            return [];
        }
        if (!res.ok) throw new Error("Failed to fetch users");
        return await res.json();
    } catch (err) {
        console.error("fetchUsers error:", err);
        return [];
    }
}
