// Уведомления — кнопка и панель
const notifBtn = document.getElementById('notifBtn');
const notifPanel = document.getElementById('notifPanel');
const notifBadge = document.getElementById('notifBadge');
const notifList = document.getElementById('notifList');

if (notifBtn) {
  // Получаем количество непрочитанных при загрузке
  fetch('/notifications/unread-count')
    .then(r => r.json())
    .then(data => {
      if (data.count > 0) {
        notifBadge.textContent = data.count;
        notifBadge.style.display = 'inline';
      }
    });

  notifBtn.addEventListener('click', () => {
    const visible = notifPanel.style.display !== 'none';
    if (visible) {
      notifPanel.style.display = 'none';
    } else {
      loadNotifications();
      notifPanel.style.display = 'flex';
      notifPanel.style.flexDirection = 'column';
    }
  });

  document.addEventListener('click', e => {
    if (!notifPanel.contains(e.target) && e.target !== notifBtn) {
      notifPanel.style.display = 'none';
    }
  });
}

function loadNotifications() {
  fetch('/notifications/list')
    .then(r => r.json())
    .then(items => {
      if (!notifList) return;
      if (items.length === 0) {
        notifList.innerHTML = '<div style="padding:1rem;color:#aaa;text-align:center">Нет уведомлений</div>';
        return;
      }
      notifList.innerHTML = items.map(n => `
        <div class="notif-item-panel" style="background:${n.is_read ? '#fff' : '#f0f0ff'}">
          <div>${n.message}</div>
          <div style="font-size:.75rem;color:#aaa;margin-top:.25rem">${n.created_at}</div>
        </div>
      `).join('');
    });
}

function markAllRead() {
  fetch('/notifications/mark-read', { method: 'POST' })
    .then(() => {
      if (notifBadge) { notifBadge.style.display = 'none'; }
      loadNotifications();
    });
}

// Автоматически скрывать flash-сообщения через 4 секунды
document.querySelectorAll('.alert').forEach(el => {
  setTimeout(() => { el.style.transition = 'opacity .5s'; el.style.opacity = '0'; setTimeout(() => el.remove(), 500); }, 4000);
});
