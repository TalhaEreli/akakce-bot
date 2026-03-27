import os
import time
import json
import requests
from datetime import datetime

# ─── AYARLAR ────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN  = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID         = os.environ.get("CHAT_ID", "")
CHECK_INTERVAL  = int(os.environ.get("CHECK_INTERVAL", "1800"))

# Takip edilecek ürünler  →  { akakce_product_id: hedef_fiyat_TL }
# 0 = herhangi bir düşüşte bildir
PRODUCTS = {
    "636410600":  0,       # MSI MAG Pano M100R PZ Kasa          (~4.599 TL)
    "122734499":  0,       # MSI MAG A750GL 750W PSU              (~5.595 TL)
    "1457209024": 0,       # Kioxia Exceria PRO 1TB SSD           (~8.462 TL)
    "774247849":  0,       # Patriot Viper Venom 16GB DDR5 CL30  (~11.419 TL)
    "1341833908": 0,       # MSI PRO B850M-G Anakart              (~6.219 TL)
    "965200325":  0,       # Sapphire RX 9070 XT Pulse            (~34.361 TL)
    "277759349":  0,       # Thermalright PA 120 SE ARGB          (~2.199 TL)
    "334009206":  0,       # AMD Ryzen 7 7800X3D                  (~15.607 TL)
}

# Farklı User-Agent'lar — her istekte rastgele seç
USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "akakce/9.5.0 (Android 13; Samsung SM-G991B)",
    "akakce/9.4.2 (iOS 17.0; iPhone14,3)",
]

import random

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "tr-TR,tr;q=0.9",
        "Referer": "https://www.akakce.com/",
        "Origin": "https://www.akakce.com",
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

# ─── FİYAT ÇEK ───────────────────────────────────────────────────────────────
def get_price(product_id: str):
    """Birkaç farklı endpoint dener, ilk çalışandan fiyatı döner."""

    endpoints = [
        f"https://www.akakce.com/p.json?p={product_id}&v=9",
        f"https://www.akakce.com/fiyat.json?p={product_id}",
        f"https://api.akakce.com/p/?p={product_id}",
    ]

    for url in endpoints:
        try:
            r = requests.get(url, headers=get_headers(), timeout=15)
            if r.status_code == 200:
                try:
                    data = r.json()
                    # Olası alanlar
                    price = (data.get("p") or data.get("minPrice")
                             or data.get("price") or data.get("min_price"))
                    name  = (data.get("n") or data.get("name")
                             or data.get("productName") or f"Ürün #{product_id}")
                    if price:
                        return float(price), str(name)
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(1)

    # Son çare: HTML sayfasını parse et
    try:
        import re
        url_html = f"https://www.akakce.com/p/?p={product_id}"
        r = requests.get(url_html, headers=get_headers(), timeout=20)
        text = r.text

        # JSON-LD veya meta fiyat ara
        m = re.search(r'"price"\s*:\s*"?([\d,\.]+)"?', text)
        n = re.search(r'<h1[^>]*class="[^"]*pn[^"]*"[^>]*>([^<]+)</h1>', text)
        if not n:
            n = re.search(r'<title>([^<|]+)', text)

        if m:
            price_str = m.group(1).replace(",", ".")
            price = float(price_str)
            name  = n.group(1).strip() if n else f"Ürün #{product_id}"
            return price, name
    except Exception:
        pass

    return None, None

# ─── TELEGRAM ────────────────────────────────────────────────────────────────
def send_telegram(text: str):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("[UYARI] Token veya Chat ID eksik!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=10)
        if r.status_code != 200:
            print(f"[HATA] Telegram: {r.text}")
    except Exception as e:
        print(f"[HATA] Telegram gönderim: {e}")

# ─── KONTROL ─────────────────────────────────────────────────────────────────
def check_prices():
    known   = load_prices()
    updated = False
    alerts  = []

    for pid, target in PRODUCTS.items():
        price, name = get_price(pid)
        ts = datetime.now().strftime("%d.%m %H:%M")

        if price is None:
            print(f"[{ts}] {pid} → fiyat alınamadı")
            time.sleep(5)
            continue

        prev = known.get(pid, {}).get("price")
        known.setdefault(pid, {})
        known[pid]["name"]  = name
        known[pid]["price"] = price
        updated = True

        akakce_url = f"https://www.akakce.com/p/?p={pid}"

        if prev is None:
            print(f"[{ts}] İlk kayıt → {name[:45]} | {price:,.2f} TL")

        elif price < prev:
            diff = prev - price
            pct  = diff / prev * 100
            msg  = (
                f"🔥 <b>FİYAT DÜŞTÜ!</b>\n"
                f"📦 {name}\n"
                f"💰 <b>{price:,.2f} TL</b>  "
                f"<s>{prev:,.2f} TL</s>\n"
                f"📉 -{diff:,.2f} TL  (-%{pct:.1f})\n"
                f"🔗 <a href='{akakce_url}'>Akakçe'de gör</a>\n"
                f"🕐 {ts}"
            )
            if target == 0 or price <= target:
                alerts.append(msg)
            print(f"[{ts}] DÜŞTÜ → {name[:45]} | {prev:,.2f} → {price:,.2f} TL")

        elif price > prev:
            print(f"[{ts}] Yükseldi → {name[:45]} | {prev:,.2f} → {price:,.2f} TL")

        else:
            print(f"[{ts}] Değişmedi → {name[:45]} | {price:,.2f} TL")

        time.sleep(4)

    if updated:
        save_prices(known)

    for alert in alerts:
        send_telegram(alert)

    if not alerts:
        print(f"[{datetime.now():%H:%M}] Bildirim yok — sonraki kontrol {CHECK_INTERVAL//60} dk sonra")

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  Akakçe Fiyat Takip Botu v2 başlatıldı")
    print(f"  Kontrol aralığı : {CHECK_INTERVAL // 60} dakika")
    print(f"  Takip edilen    : {len(PRODUCTS)} ürün")
    print("=" * 55)

    send_telegram(
        "✅ <b>Akakçe Fiyat Botu v2 başladı!</b>\n"
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
