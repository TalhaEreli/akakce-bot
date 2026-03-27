# Akakçe Fiyat Takip Botu — Kurulum Rehberi

## Ne yapar?
Her 30 dakikada Akakçe'deki 8 ürünün fiyatını kontrol eder.
Fiyat düşünce Telegram'a bildirim atar.

---

## ADIM 1 — Telegram Bot Token al (2 dakika)

1. Telegram'da **@BotFather**'ı aç
2. `/newbot` yaz
3. Bot için bir isim gir → örn: `PC Fiyat Takip`
4. Kullanıcı adı gir → örn: `pcfiyattakip_bot`
5. BotFather sana şöyle bir token verecek:
   ```
   1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```
   Bunu kopyala, kaydet.

---

## ADIM 2 — Chat ID'ni öğren (1 dakika)

1. Yeni botuna bir mesaj at (herhangi bir şey yaz)
2. Tarayıcıda şu linki aç:
   ```
   https://api.telegram.org/botTOKEN_BURAYA/getUpdates
   ```
   TOKEN_BURAYA yerine az önce aldığın token'ı yaz.
3. Çıkan JSON'da `"id"` yazan sayıyı bul → bu senin Chat ID'n
   ```json
   {"message":{"chat":{"id": 123456789}}}
   ```

---

## ADIM 3 — GitHub'a yükle (3 dakika)

1. **github.com** → Sign Up (hesap aç, ücretsiz)
2. **New repository** → İsim: `akakce-bot` → Public → Create
3. Bilgisayarında şu 3 dosyayı yükle:
   - `bot.py`
   - `requirements.txt`
   - `Procfile`

   > Upload files butonuyla sürükle bırak yeterli!

---

## ADIM 4 — Railway'e deploy et (5 dakika)

1. **railway.app** → Google ile giriş yap
2. **New Project** → **Deploy from GitHub repo**
3. `akakce-bot` reposunu seç
4. Sol menüden **Variables** sekmesine tıkla
5. Şu 2 değişkeni ekle:

   | İsim | Değer |
   |------|-------|
   | `TELEGRAM_TOKEN` | `1234567890:ABCdef...` |
   | `CHAT_ID` | `123456789` |

6. **Deploy** butonuna bas

---

## ✅ Hazır!

Bot başlayınca Telegram'a şu mesajı atacak:
```
✅ Akakçe Fiyat Botu başladı!
📊 8 ürün takip ediliyor
⏱ Her 30 dakikada kontrol edilecek
```

Fiyat düşünce şunu alacaksın:
```
🔥 FİYAT DÜŞTÜ!
📦 Sapphire RX 9070 XT Pulse...
💰 32.500 TL  ~~34.361 TL~~
📉 -1.861 TL  (-%5.4)
🔗 Akakçe'de gör
🕐 27.03 14:32
```

---

## Sorun giderme

**Bot mesaj atmıyor?**
- Railway → Logs sekmesini kontrol et
- Token ve Chat ID doğru girildi mi?

**"fiyat alınamadı" hatası?**
- Akakçe geçici olarak erişimi engelliyor olabilir
- 30 dakika sonra tekrar dener, sorun değil

---

## Fiyat hedefi koymak (opsiyonel)

`bot.py` dosyasında `PRODUCTS` bölümünde `0` yerine hedef fiyat yaz:
```python
"334009206": 13000,  # 7800X3D için sadece 13.000 TL altında bildir
```
