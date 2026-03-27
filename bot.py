import os, re, time, json, random, requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID        = os.environ.get("CHAT_ID", "")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "1800"))
DATA_FILE      = "prices.json"

PRODUCTS = {
    "kasa": {
        "isim": "MSI MAG Pano M100R PZ Kasa (Siyah)",
        "hedef": 0,
        "kaynaklar": [
            {"site": "amazon",    "id": "B0CN1HK8P5"},
            {"site": "incehesap", "id": "msi-mag-pano-m100r-pz-4-argb-fanli-siyah-micro-atx-oyuncu-kasasi-fiyatlari"},
        ],
    },
    "psu": {
        "isim": "MSI MAG A750GL 750W 80+ Gold PSU",
        "hedef": 0,
        "kaynaklar": [
            {"site": "amazon",    "id": "B0C79GBL8L"},
            {"site": "hepsi_api", "id": "msi-mag-a750gl-pcie5-750w-80-gold-full-modueler-guc-kaynagi-pm-HBC00009OVKLS"},
            {"site": "incehesap", "id": "msi-mag-a750gl-pcie5-750w-80-gold-full-moduler-guc-kaynagi-fiyatlari"},
        ],
    },
    "ssd": {
        "isim": "Kioxia Exceria PRO 1TB NVMe",
        "hedef": 0,
        "kaynaklar": [
            {"site": "hepsi_api", "id": "kioxia-exceria-pro-lse10z001tg8-1-tb-7300-6400-mb-s-m-2-ssd-disk-pm-HBC0000665247288"},
            {"site": "incehesap", "id": "kioxia-exceria-pro-lse10z001tg8-pci-express-4-0-1-tb-m-2-ssd-fiyatlari"},
        ],
    },
    "ram": {
        "isim": "Patriot Viper Venom 16GB DDR5 6000 CL30",
        "hedef": 0,
        "kaynaklar": [
            {"site": "incehesap", "id": "patriot-viper-venom-pvv516g60c30-16-gb-6000-mhz-cl30-ddr5-ram-fiyatlari"},
        ],
    },
    "anakart": {
        "isim": "MSI PRO B850M-G AM5 Anakart",
        "hedef": 0,
        "kaynaklar": [
            {"site": "amazon",    "id": "B0D7Q5KXNK"},
            {"site": "hepsi_api", "id": "msi-pro-b850m-g-am5-ddr5-8200-oc-mhz-matx-anakart-pm-HBC0000CDBMDX"},
            {"site": "incehesap", "id": "msi-pro-b850m-g-amd-am5-ddr5-micro-atx-anakart-fiyatlari"},
        ],
    },
    "gpu": {
        "isim": "Sapphire RX 9070 XT Pulse 16GB",
        "hedef": 0,
        "kaynaklar": [
            {"site": "hepsi_api", "id": "sapphire-rx-9070-xt-pulse-11348-03-20g-256-bit-gddr6-16-gb-ekran-karti-pm-HBC0000879L6A"},
            {"site": "incehesap", "id": "sapphire-rx-9070-xt-pulse-11348-03-20g-256-bit-gddr6-16-gb-ekran-karti-fiyatlari"},
        ],
    },
    "sogutucu": {
        "isim": "Thermalright Peerless Assassin 120 SE ARGB",
        "hedef": 0,
        "kaynaklar": [
            {"site": "hepsi_api", "id": "thermalright-peerless-assassin-120-se-argb-siyah-islemci-sogutucu-pm-HBC00009KGJID"},
        ],
    },
    "cpu": {
        "isim": "AMD Ryzen 7 7800X3D",
        "hedef": 0,
        "kaynaklar": [
            {"site": "amazon",    "id": "B0CJML6LQZ"},
            {"site": "hepsi_api", "id": "amd-ryzen-7-7800x3d-sekiz-cekirdek-4-2-ghz-islemci-pm-HBC00006BIHVF"},
        ],
    },
}

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]

def hdrs(ref=""):
    h = {
        "User-Agent": random.choice(UA_LIST),
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }
    if ref:
        h["Referer"] = ref
    return h

# ── AMAZON TR ────────────────────────────────────────
def parse_tr_price(raw: str):
    """
    Türkçe fiyat formatını float'a çevirir.
    "4.661,76" → 4661.76
    "466,176"  → 466176.0  (yanlış — bu büyük sayı)
    Mantık: son virgülden sonra 2 hane varsa decimal, yoksa binlik.
    """
    raw = raw.strip().replace("\xa0", "").replace(" ", "")
    # "4.661,76" formatı: nokta=binlik, virgül=decimal
    if "," in raw and "." in raw:
        # nokta binlik, virgül decimal
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        parts = raw.split(",")
        if len(parts[-1]) == 2:
            # "4661,76" → decimal
            raw = raw.replace(",", ".")
        else:
            # "466,176" → binlik virgül yok decimal
            raw = raw.replace(",", "")
    elif "." in raw:
        parts = raw.split(".")
        if len(parts[-1]) == 2:
            # "4661.76" → decimal nokta
            pass
        else:
            # "4.661" → binlik nokta
            raw = raw.replace(".", "")
    try:
        return float(raw)
    except:
        return None

def price_amazon(asin: str):
    url = f"https://www.amazon.com.tr/dp/{asin}"
    try:
        r = requests.get(url, headers=hdrs("https://www.amazon.com.tr/"), timeout=20)
        t = r.text
        patterns = [
            r'"priceAmount"\s*:\s*([\d,\.]+)',
            r'class="a-price-whole">([\d.,]+)',
            r'id="priceblock_ourprice"[^>]*>([\d.,\s]+)',
            r'"displayPrice"\s*:\s*"([\d.,]+)\s*TL"',
            r'<span[^>]+class="[^"]*a-color-price[^"]*"[^>]*>([\d.,]+)',
        ]
        for pat in patterns:
            m = re.search(pat, t)
            if m:
                p = parse_tr_price(m.group(1))
                if p and 100 < p < 500_000:
                    return p
    except Exception as e:
        print(f"    [amazon/{asin}] {e}")
    return None

# ── HEPSİBURADA ─────────────────────────────────────
def price_hepsiburada(slug_with_hbc: str):
    """slug_with_hbc: tam ürün URL slug'ı (pm-HBC... dahil)"""
    url = f"https://www.hepsiburada.com/{slug_with_hbc}"
    try:
        r = requests.get(url, headers=hdrs("https://www.hepsiburada.com/"), timeout=20)
        t = r.text
        patterns = [
            r'"salePrice"\s*:\s*([\d]+(?:\.\d+)?)',
            r'"price"\s*:\s*([\d]+(?:\.\d+)?)',
            r'"finalPrice"\s*:\s*([\d]+(?:\.\d+)?)',
            r'data-price="([\d]+(?:\.\d+)?)"',
            r'"priceValue"\s*:\s*([\d]+(?:\.\d+)?)',
        ]
        for pat in patterns:
            m = re.search(pat, t)
            if m:
                try:
                    p = float(m.group(1))
                    if 100 < p < 500_000:
                        return p
                except:
                    pass
    except Exception as e:
        print(f"    [hb] {e}")
    return None

# ── İNCEHESAP ────────────────────────────────────────
def price_incehesap(slug: str):
    url = f"https://www.incehesap.com/{slug}/"
    try:
        r = requests.get(url, headers=hdrs("https://www.incehesap.com/"), timeout=20)
        t = r.text
        patterns = [
            r'"price"\s*:\s*"?([\d]+(?:[,\.]\d+)?)"?',
            r'"lowPrice"\s*:\s*"?([\d]+(?:[,\.]\d+)?)"?',
            r'class="[^"]*fiyat[^"]*"[^>]*>([\d.,]+)',
            r'itemprop="price"[^>]*content="([\d.,]+)"',
            r'"offers".*?"price"\s*:\s*"?([\d.,]+)"?',
        ]
        for pat in patterns:
            m = re.search(pat, t, re.IGNORECASE | re.DOTALL)
            if m:
                p = parse_tr_price(m.group(1))
                if p and 100 < p < 500_000:
                    return p
    except Exception as e:
        print(f"    [incehesap] {e}")
    return None

# ── MIN FİYAT ────────────────────────────────────────
def get_min_price(pid, product):
    prices = {}
    for src in product["kaynaklar"]:
        site = src["site"]
        uid  = src["id"]
        p = None
        if site == "amazon":
            p = price_amazon(uid)
        elif site == "hepsi_api":
            p = price_hepsiburada(uid)
        elif site == "incehesap":
            p = price_incehesap(uid)
        if p:
            prices[site] = p
            label = site.replace("hepsi_api", "hepsiburada")
            print(f"    {label:12s} → {p:,.2f} TL")
        time.sleep(2)
    if not prices:
        return None, None
    best = min(prices, key=prices.get)
    return prices[best], best.replace("hepsi_api", "hepsiburada")

# ── TELEGRAM ─────────────────────────────────────────
def send_tg(text):
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
        print(f"[TG] {e}")

# ── VERİ ─────────────────────────────────────────────
def load():
    return json.load(open(DATA_FILE, encoding="utf-8")) if os.path.exists(DATA_FILE) else {}

def save(d):
    json.dump(d, open(DATA_FILE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

# ── KONTROL ──────────────────────────────────────────
def check():
    known  = load()
    ts     = datetime.now().strftime("%d.%m %H:%M")
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
            msg  = (
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

# ── MAIN ─────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  Fiyat Takip Botu v4  (Amazon / HB / İncehesap)")
    print(f"  {len(PRODUCTS)} ürün  |  {CHECK_INTERVAL//60} dk aralık")
    print("=" * 55)
    send_tg(
        "✅ <b>Fiyat Botu v4 başladı!</b>\n"
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
