const errorBox = document.getElementById("error");

async function doLogin() {
  errorBox.innerHTML = "";
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  if (!username || !password) {
    errorBox.innerHTML = '<div class="msg err">Enter username and password.</div>';
    return;
  }
  try {
    const data = await api("/auth/login/", "POST", { username, password });
    localStorage.setItem("token", data.token);
    localStorage.setItem("role", data.role);
    localStorage.setItem("name", data.name);
    window.location.href = "dashboard.html";
  } catch (e) {
    errorBox.innerHTML = '<div class="msg err">' + esc(e.message) + "</div>";
  }
}

document.getElementById("loginBtn").addEventListener("click", doLogin);
document.addEventListener("keydown", e => { if (e.key === "Enter") doLogin(); });
if (getAuth().token) window.location.href = "dashboard.html";
