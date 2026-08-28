self.addEventListener('install', function(event) {
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    event.waitUntil(clients.claim());
});

self.addEventListener('push', function(event) {
    if (!(self.Notification && self.Notification.permission === 'granted')) {
        return;
    }

    let data = {};
    try {
        data = event.data.json();
    } catch (e) {
        data = {
            title: 'VEGA // MESH',
            body: 'Новое сообщение'
        };
    }

    const title = data.title || 'VEGA // MESH';
    const options = {
        body: data.body || 'Новое сообщение',
        icon: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"%3E%3Crect width="100" height="100" fill="%23030712"/%3E%3Ctext x="50" y="55" text-anchor="middle" font-size="40" fill="%2306b6d4" font-family="monospace"%3E⚡%3C/text%3E%3C/svg%3E',
        badge: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"%3E%3Crect width="100" height="100" fill="%23030712"/%3E%3Ctext x="50" y="55" text-anchor="middle" font-size="40" fill="%2306b6d4" font-family="monospace"%3E⚡%3C/text%3E%3C/svg%3E',
        vibrate: [200, 100, 200],
        silent: false,
        requireInteraction: true
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(
        clients.openWindow('/')
    );
});