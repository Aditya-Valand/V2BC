// firebase-messaging-sw.js
// Firebase Cloud Messaging service worker for background message handling.
//
// Firebase SDK requires this file at /firebase-messaging-sw.js.
// Since we pass serviceWorkerRegistration: <our sw.js> to getToken(),
// Firebase uses our sw.js for push delivery.
// This file is kept minimal as a fallback registration point.
//
// If you switch from passing a custom swReg to the default Firebase behaviour,
// uncomment the importScripts block below and fill in your Firebase config.

// importScripts('https://www.gstatic.com/firebasejs/10.12.5/firebase-app-compat.js');
// importScripts('https://www.gstatic.com/firebasejs/10.12.5/firebase-messaging-compat.js');
//
// firebase.initializeApp({
//   apiKey:            'YOUR_API_KEY',
//   authDomain:        'YOUR_AUTH_DOMAIN',
//   projectId:         'YOUR_PROJECT_ID',
//   storageBucket:     'YOUR_STORAGE_BUCKET',
//   messagingSenderId: 'YOUR_SENDER_ID',
//   appId:             'YOUR_APP_ID',
// });
//
// const messaging = firebase.messaging();
// messaging.onBackgroundMessage((payload) => {
//   const { title, body } = payload.notification || {};
//   self.registration.showNotification(title || 'BharatCompliance', {
//     body, icon: '/icons/icon-192.svg',
//   });
// });
