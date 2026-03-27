import os
import time
import json
import requests
from datetime import datetime

# ─── AYARLAR ────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID        = os.environ.get("CHAT_ID", "")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "1800"))  # saniye (varsayılan 30 dk)

# Takip edilecek ürünler  →  { akakce_product_id: hedef_fiyat_TL }
# Hedef fiyata düşünce bildirim gönderilir. 0 = herhangi bir düşüşte bildir.
PRODUCTS = {
    "636410600":  0,       # MSI MAG Pano M100R PZ Kasa          (şu an ~4.599 TL)
    "122734499":  0,       # MSI MAG A750GL 750W PSU              (şu an ~5.595 TL)
    "1457209024": 0,       # Kioxia Exceria PRO 1TB SSD           (şu an ~8.462 TL)
    "774247849":  0,       # Patriot Viper Venom 16GB DDR5 CL30  (şu an ~11.419 TL)
    "1341833908": 0,       # MSI PRO B850M-G Anakart              (şu an ~6.219 TL)
    "965200325":  0,       # Sapphire RX 9070 XT Pulse            (şu an ~34.361 TL)
    "277759349":  0,       # Thermalright PA 120 SE ARGB          (şu an ~2.199 TL)
    "334009206":  0,       # AMD Ryzen 7 7800X3D                  (şu an ~15.607 TL)
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9",
}

# ─── VERİ DOSYASI ────────────────────────────────────────────────────────────
DATA_FILE = "prices.json"

def load_prices():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_prices(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ─── AKAKÇE FİYAT ÇEK ───────────────────────────────────────────────────────
def get_price(product_id: str):
    """Akakçe ürün sayfasından güncel fiyatı çeker."""
    url = f"https://www.akakce.com/p.json?p={product_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            price = data.get("p") or data.get("minPrice")
            name  = data.get("n") or data.get("name", f"Ürün #{product_id}")
            return float(price), str(name)
    except Exception:
        pass

    # Yedek: ürün sayfasını HTML parse et
    try:
        url2 = f"https://www.akakce.com/p/?p={product_id}"
        r2 = requests.get(url2, headers=HEADERS, timeout=15)
        import re
        m = re.search(r'"price":\s*([\d.]+)', r2.text)
        n = re.search(r'<title>([^<]+)</title>', r2.text)
        if m:
            price = float(m.group(1))
            name  = n.group(1).strip() if n else f"Ürün #{product_id}"
            return price, name
    except Exception:
        pass

    return None, None

# ─── TELEGRAM MESAJ ─────────────────────────────────────────────────────────
def send_telegram(text: str):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("[UYARI] TELEGRAM_TOKEN veya CHAT_ID tanımlı değil!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=10)
    except Exception as e:
        print(f"[HATA] Telegram mesajı gönderilemedi: {e}")

# ─── ANA DÖNGÜ ───────────────────────────────────────────────────────────────
def check_prices():
    known = load_prices()
    updated = False
    alerts = []

    for pid, target in PRODUCTS.items():
        price, name = get_price(pid)
        if price is None:
            print(f"[{datetime.now():%H:%M}] {pid} → fiyat alınamadı")
            time.sleep(2)
            continue

        prev = known.get(pid, {}).get("price")
        known.setdefault(pid, {})
        known[pid]["name"]  = name
        known[pid]["price"] = price
        updated = True

        url = f"https://www.akakce.com/p/?p={pid}"
        ts  = datetime.now().strftime("%d.%m %H:%M")

        if prev is None:
            print(f"[{ts}] İlk kayıt → {name[:40]} | {price:,.2f} TL")
        elif price < prev:
            diff = prev - price
            pct  = diff / prev * 100
            msg  = (
                f"🔥 <b>FİYAT DÜŞTÜ!</b>\n"
                f"📦 {name}\n"
                f"💰 <b>{price:,.2f} TL</b>  "
                f"<s>{prev:,.2f} TL</s>\n"
                f"📉 -{diff:,.2f} TL  (-%{pct:.1f})\n"
                f"🔗 <a href='{url}'>Akakçe'de gör</a>\n"
                f"🕐 {ts}"
            )
            if target == 0 or price <= target:
                alerts.append(msg)
            print(f"[{ts}] DÜŞTÜ → {name[:40]} | {prev:,.2f} → {price:,.2f} TL")
        elif price > prev:
            diff = price - prev
            print(f"[{ts}] Yükseldi → {name[:40]} | {prev:,.2f} → {price:,.2f} TL (+{diff:,.2f})")
        else:
            print(f"[{ts}] Değişmedi → {name[:40]} | {price:,.2f} TL")

        time.sleep(3)  # Akakçe'yi çok sık çarpmamak için bekle

    if updated:
        save_prices(known)

    for alert in alerts:
        send_telegram(alert)

    if not alerts:
        print(f"[{datetime.now():%H:%M}] Bildirim yok — sonraki kontrol {CHECK_INTERVAL//60} dk sonra")


def main():
    print("=" * 55)
    print("  Akakçe Fiyat Takip Botu başlatıldı")
    print(f"  Kontrol aralığı: {CHECK_INTERVAL // 60} dakika")
    print(f"  Takip edilen ürün sayısı: {len(PRODUCTS)}")
    print("=" * 55)

    send_telegram(
        "✅ <b>Akakçe Fiyat Botu başladı!</b>\n"
        f"📊 {len(PRODUCTS)} ürün takip ediliyor\n"
        f"⏱ Her {CHECK_INTERVAL // 60} dakikada kontrol edilecek"
    )

    while True:
        try:
            check_prices()
        except Exception as e:
            print(f"[HATA] {e}")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
