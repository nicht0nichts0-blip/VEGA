// Service Worker: работает в фоне даже при закрытом браузере
self.addEventListener('push', function(event) {
    let data = { title: 'CYPHER // MESH', body: '🔒 Новое зашифрованное сообщение!' };

    if (event.data) {
        try {
            data = event.data.json();
        } catch(e) {
            data.body = event.data.text();
        }
    }

    const options = {
        body: data.body,
        icon: 'https://fav.farm/🔒',
        badge: 'https://fav.farm/💬',
        vibrate: [100, 50, 100],
        data: { dateOfArrival: Date.now() }
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Клик по уведомлению открывает сайт
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(
        clients.openWindow('/')
    );
});
