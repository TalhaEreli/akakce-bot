import os, re, time, json, random, requests
from datetime import datetime

# ══════════════════════════════════════════════════════
#  AYARLAR
# ══════════════════════════════════════════════════════
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID        = os.environ.get("CHAT_ID", "")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "1800"))  # 30 dk
DATA_FILE      = "prices.json"

# ══════════════════════════════════════════════════════
#  ÜRÜN LİSTESİ
#  Format: { "benzersiz_id": { "isim", "hedef", "kaynaklar": [...] } }
#  kaynak: { "site": "amazon|hepsiburada|incehesap", "id": "..." }
#    amazon      → ASIN  (örn. B0CN1HK8P5)
#    hepsiburada → HBC kodu (örn. HBC0000879L6A)
#    incehesap   → ürün slug veya tam URL son parçası
# ══════════════════════════════════════════════════════
PRODUCTS = {
    "kasa": {
        "isim": "MSI MAG Pano M100R PZ Kasa (Siyah)",
        "hedef": 0,
        "kaynaklar": [
            {"site": "amazon",      "id": "B0CN1HK8P5"},
            {"site": "incehesap",   "id": "msi-mag-pano-m100r-pz-4-argb-fanli-siyah-micro-atx-oyuncu-kasasi"},
        ],
    },
    "psu": {
        "isim": "MSI MAG A750GL 750W 80+ Gold PSU",
        "hedef": 0,
        "kaynaklar": [
            {"site": "amazon",      "id": "B0C79GBL8L"},
            {"site": "hepsiburada", "id": "HBC00009OVKLS"},
            {"site": "incehesap",   "id": "msi-mag-a750gl-pcie5-750w-80-gold-full-moduler-guc-kaynagi"},
        ],
    },
    "ssd": {
        "isim": "Kioxia Exceria PRO 1TB NVMe PCIe 4.0",
        "hedef": 0,
        "kaynaklar": [
            {"site": "hepsiburada", "id": "HBC0000665247"},
            {"site": "incehesap",   "id": "kioxia-exceria-pro-lse10z001tg8-1tb-7300-6400mb-s-m-2-nvme-ssd"},
        ],
    },
    "ram": {
        "isim": "Patriot Viper Venom 16GB DDR5 6000MHz CL30",
        "hedef": 0,
        "kaynaklar": [
            {"site": "incehesap",   "id": "patriot-viper-venom-pvv516g60c30-16gb-1x16gb-ddr5-6000mhz-cl30-gaming-ram"},
        ],
    },
    "anakart": {
        "isim": "MSI PRO B850M-G AM5 Anakart",
        "hedef": 0,
        "kaynaklar": [
            {"site": "amazon",      "id": "B0D7Q5KXNK"},
            {"site": "hepsiburada", "id": "HBC0000CDBMDX"},
            {"site": "incehesap",   "id": "msi-pro-b850m-g-am5-ddr5-8200-oc-mhz-matx-anakart"},
        ],
    },
    "gpu": {
        "isim": "Sapphire RX 9070 XT Pulse 16GB",
        "hedef": 0,
        "kaynaklar": [
            {"site": "hepsiburada", "id": "HBC0000879L6A"},
            {"site": "incehesap",   "id": "sapphire-rx-9070-xt-pulse-11348-03-20g-256-bit-gddr6-16-gb-ekran-karti"},
        ],
    },
    "sogutucu": {
        "isim": "Thermalright Peerless Assassin 120 SE ARGB",
        "hedef": 0,
        "kaynaklar": [
            {"site": "hepsiburada", "id": "HBC00009KGJID"},
        ],
    },
    "cpu_7800x3d": {
        "isim": "AMD Ryzen 7 7800X3D",
        "hedef": 0,
        "kaynaklar": [
            {"site": "hepsiburada", "id": "HBC00006BIHVF"},
            {"site": "amazon",      "id": "B0CJML6LQZ"},
        ],
    },
}

# ══════════════════════════════════════════════════════
#  HEADERS
# ══════════════════════════════════════════════════════
def hdrs(ref=""):
    ua = random.choice([
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ])
    h = {"User-Agent": ua, "Accept-Language": "tr-TR,tr;q=0.9", "Accept": "text/html,*/*;q=0.8"}
    if ref:
        h["Referer"] = ref
    return h

# ══════════════════════════════════════════════════════
#  AMAZON TR — fiyat çek
# ══════════════════════════════════════════════════════
def price_amazon(asin: str):
    url = f"https://www.amazon.com.tr/dp/{asin}"
    try:
        r = requests.get(url, headers=hdrs("https://www.amazon.com.tr/"), timeout=20)
        t = r.text
        # Çeşitli pattern'ler
        for pat in [
            r'"priceAmount"\s*:\s*([\d]+(?:\.\d+)?)',
            r'class="a-price-whole">([0-9.,]+)',
            r'"price":\s*"([\d.,]+)\s*TL"',
            r'priceblock_ourprice[^>]*>([\d.,]+)',
        ]:
            m = re.search(pat, t)
            if m:
                p = float(m.group(1).replace(".", "").replace(",", "."))
                if p > 10:
                    return p
    except Exception as e:
        print(f"    [amazon/{asin}] {e}")
    return None

# ══════════════════════════════════════════════════════
#  HEPSİBURADA — fiyat çek
# ══════════════════════════════════════════════════════
def price_hepsiburada(hbc: str):
    # Hepsiburada ürün URL'si slug gerektiriyor; slug bilinmiyorsa arama yap
    search_url = f"https://www.hepsiburada.com/ara?q={hbc}"
    try:
        r = requests.get(search_url, headers=hdrs("https://www.hepsiburada.com/"), timeout=20)
        t = r.text
        # JSON içinde fiyat ara
        for pat in [
            r'"salePrice"\s*:\s*([\d]+(?:\.\d+)?)',
            r'"price"\s*:\s*([\d]+(?:\.\d+)?)',
            r'"finalPrice"\s*:\s*([\d]+(?:\.\d+)?)',
            r'data-price="([\d]+(?:[.,]\d+)?)"',
        ]:
            m = re.search(pat, t)
            if m:
                p = float(str(m.group(1)).replace(",", "."))
                if p > 10:
                    return p
    except Exception as e:
        print(f"    [hb/{hbc}] {e}")
    return None

# ══════════════════════════════════════════════════════
#  İNCEHESAP — fiyat çek
# ══════════════════════════════════════════════════════
def price_incehesap(slug: str):
    url = f"https://www.incehesap.com/{slug}-fiyati/"
    try:
        r = requests.get(url, headers=hdrs("https://www.incehesap.com/"), timeout=20)
        t = r.text
        for pat in [
            r'"price"\s*:\s*"?([\d]+(?:[.,]\d+)?)"?',
            r'class="[^"]*price[^"]*"[^>]*>([\d.,]+)',
            r'fiyat[^>]*>([\d.,]+)\s*TL',
            r'"lowPrice"\s*:\s*"?([\d]+(?:[.,]\d+)?)"?',
        ]:
            m = re.search(pat, t, re.IGNORECASE)
            if m:
                raw = m.group(1).replace(".", "").replace(",", ".")
                try:
                    p = float(raw)
                    if p > 10:
                        return p
                except:
                    pass
    except Exception as e:
        print(f"    [incehesap/{slug[:30]}] {e}")
    return None

# ══════════════════════════════════════════════════════
#  MİN FİYAT AL
# ══════════════════════════════════════════════════════
def get_min_price(pid: str, product: dict):
    """Tüm kaynaklardan fiyat çeker, en düşüğü döner."""
    prices = {}
    for src in product["kaynaklar"]:
        site = src["site"]
        uid  = src["id"]
        p = None
        if site == "amazon":
            p = price_amazon(uid)
        elif site == "hepsiburada":
            p = price_hepsiburada(uid)
        elif site == "incehesap":
            p = price_incehesap(uid)
        if p:
            prices[site] = p
            print(f"    {site:12s} → {p:,.2f} TL")
        time.sleep(2)

    if not prices:
        return None, None
    min_site  = min(prices, key=prices.get)
    min_price = prices[min_site]
    return min_price, min_site

# ══════════════════════════════════════════════════════
#  TELEGRAM
# ══════════════════════════════════════════════════════
def send_tg(text: str):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10
        )
    except Exception as e:
        print(f"[TG HATA] {e}")

# ══════════════════════════════════════════════════════
#  VERİ
# ══════════════════════════════════════════════════════
def load():
    return json.load(open(DATA_FILE, encoding="utf-8")) if os.path.exists(DATA_FILE) else {}

def save(d):
    json.dump(d, open(DATA_FILE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

# ══════════════════════════════════════════════════════
#  ANA DÖNGÜ
# ══════════════════════════════════════════════════════
def check():
    known = load()
    ts    = datetime.now().strftime("%d.%m %H:%M")
    alerts = []

    for pid, prod in PRODUCTS.items():
        name   = prod["isim"]
        target = prod["hedef"]
        print(f"\n[{ts}] {name}")

        price, site = get_min_price(pid, prod)

        if price is None:
            print(f"  → fiyat alınamadı")
            continue

        prev = known.get(pid, {}).get("price")
        known.setdefault(pid, {})
        known[pid].update({"name": name, "price": price, "site": site})

        if prev is None:
            print(f"  → İlk kayıt: {price:,.2f} TL ({site})")
        elif price < prev:
            diff = prev - price
            pct  = diff / prev * 100
            msg = (
                f"🔥 <b>FİYAT DÜŞTÜ!</b>\n"
                f"📦 {name}\n"
                f"💰 <b>{price:,.2f} TL</b>  <s>{prev:,.2f} TL</s>\n"
                f"📉 -{diff:,.2f} TL  (-%{pct:.1f})\n"
                f"🏪 En ucuz: <b>{site}</b>\n"
                f"🕐 {ts}"
            )
            if target == 0 or price <= target:
                alerts.append(msg)
            print(f"  → DÜŞTÜ: {prev:,.2f} → {price:,.2f} TL ({site})")
        elif price > prev:
            print(f"  → Yükseldi: {prev:,.2f} → {price:,.2f} TL")
        else:
            print(f"  → Değişmedi: {price:,.2f} TL")

    save(known)
    for a in alerts:
        send_tg(a)
    if not alerts:
        print(f"\n[{ts}] Bildirim yok — {CHECK_INTERVAL//60} dk sonra tekrar.")

# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════
def main():
    print("=" * 55)
    print("  Fiyat Takip Botu v3  (Amazon TR / HB / İncehesap)")
    print(f"  {len(PRODUCTS)} ürün  |  {CHECK_INTERVAL//60} dk aralık")
    print("=" * 55)
    send_tg(
        "✅ <b>Fiyat Botu v3 başladı!</b>\n"
        f"📊 {len(PRODUCTS)} ürün takip ediliyor\n"
        f"🏪 Amazon TR · Hepsiburada · İncehesap\n"
        f"⏱ Her {CHECK_INTERVAL//60} dakikada kontrol"
    )
    while True:
        try:
            check()
        except Exception as e:
            print(f"[HATA] {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
