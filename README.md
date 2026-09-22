# कोट-व्हिडिओ Telegram बॉट — सेटअप मार्गदर्शक

## यात काय आहे
- `bot.py` — मुख्य बॉट कोड
- `videomaker.py` — फोटो आणून, झूम इफेक्ट + कोट टाकून व्हिडिओ बनवतो
- `quotes.py` — मोटिवेशनल आणि प्रेम/भावनिक कोट्सची यादी (गरज असल्यास इथे नवीन कोट टाकता येतील)
- `requirements.txt` — लागणारी Python पॅकेजेस
- `Dockerfile` — Render ला ffmpeg इन्स्टॉल करायला सांगणारी फाईल

## लागणारी खाती (सगळी मोफत)
1. Telegram — आधीच आहे ✅
2. Pexels (pexels.com/api) — फोटोंसाठी
3. GitHub (github.com) — कोड ठेवायला, Render इथून कोड उचलतो
4. Render (render.com) — बॉट २४ तास चालू ठेवायला

## पुढच्या पायऱ्या (सगळ्या गोष्टी तयार झाल्यावर एकत्र करू)
1. GitHub वर नवीन repository बनवून ही फाईल्स अपलोड करणे (drag-and-drop, कोडिंग कमांड लागत नाही)
2. Render वर "New Web Service" निवडून तो GitHub repository जोडणे, Environment "Docker" निवडणे
3. Render च्या Environment Variables मध्ये टाकायचे:
   - `TELEGRAM_BOT_TOKEN` = BotFather कडून मिळालेला token
   - `PEXELS_API_KEY` = Pexels कडून मिळालेली key
4. Deploy दाबले की काही मिनिटांत बॉट चालू होईल
5. Telegram मध्ये तुमच्या बॉटला `/start` पाठवून टेस्ट करणे

एकही पायरी अवघड कमांड-लाईन लागणार नाही, सगळे वेबसाइटवर क्लिक करून होईल.
