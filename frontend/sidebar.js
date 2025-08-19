document.addEventListener("DOMContentLoaded", () => {
    const username = localStorage.getItem('username');
    const role = localStorage.getItem('role');
    const sidebar = document.getElementById('sidebar');

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
                localStorage.removeItem('username');
                localStorage.removeItem('role');
                localStorage.removeItem('token');
                window.location.href = '/static/index.html';
            }
        } catch (error) {
            console.error('Logout failed', error);
        }
    });
});
