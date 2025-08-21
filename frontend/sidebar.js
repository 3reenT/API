document.addEventListener("DOMContentLoaded", async () => {
    const sidebar = document.getElementById('sidebar');

    try {
        const res = await fetch('/me', {
            method: 'GET',
            credentials: 'include'
        });

        if (!res.ok) {
            window.location.href = '/';
            return;
        }

        const data = await res.json();
        const username = data.username || "User";
        const role = data.role || "user"; 

        let menu = `<h3>Menu</h3>`;

        if (role === 'admin') {
            menu += `
                <a href="/static/users.html"><i class="fas fa-users"></i> Users</a>
                <a href="/static/user_posts.html"><i class="fas fa-file-alt"></i> Posts</a>
            `;
        } else {
            menu += `
                <a href="/static/user_posts.html"><i class="fas fa-file-alt"></i> Posts</a>
            `;
        }

        sidebar.innerHTML = `
            <div class="menu-items">
                ${menu}
            </div>
            <div class="user-info">
                <p>${username}</p>
                <a href="#" id="confirm-logout"><i class="fas fa-sign-out-alt"></i> Log out</a>
            </div>
        `;

        document.getElementById('confirm-logout').addEventListener('click', async (e) => {
            e.preventDefault();
            try {
                const res = await fetch('/logout', {
                    method: 'POST',
                    credentials: 'include'
                });
                if (res.ok) {
                    window.location.href = '/'; 
                }
            } catch (error) {
                console.error('Logout failed', error);
            }
        });

    } catch (error) {
        console.error("Error loading sidebar:", error);
        window.location.href = '/';
    }
});
