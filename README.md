# Chat UI - Frontend (React + Vite)

واجهة المستخدم لمشروع Personalized Chatbot - DEPI AI & Data Science Track.

## تشغيل المشروع

```bash
npm install
npm run dev
```

افتح الرابط اللي بيظهر (عادةً `http://localhost:5173`).

> الـ UI شغال حالياً على **بيانات وهمية** - مفيش backend متوصل لسه، بس كل الشكل والوظائف تقدر تتجربها.

## هيكل الملفات

```
src/
  App.jsx               الـ state الرئيسي للتطبيق
  api.js                الملف الوحيد اللي بيتكلم مع الـ backend
  components/
    Sidebar.jsx          قائمة المحادثات
    ChatWindow.jsx       نافذة الشات
    MessageBubble.jsx    رسالة واحدة
    MessageInput.jsx     صندوق الكتابة
    TypingIndicator.jsx  نقاط التحميل
```

## توصيل الـ Backend

لما الـ backend يكون جاهز:

1. في `src/api.js` غير `USE_MOCK = true` إلى `USE_MOCK = false`
2. انسخ `.env.example` إلى `.env` وحط رابط الـ FastAPI في `VITE_API_URL`
