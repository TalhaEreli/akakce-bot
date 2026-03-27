import os, re, time, json, random, requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID        = os.environ.get("CHAT_ID", "")
SCRAPER_KEY    = os.environ.get("SCRAPER_KEY", "")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "1800"))
DATA_FILE      = "prices.json"

PRODUCTS = {
    "kasa": {
        "isim": "MSI MAG Pano M100R PZ Kasa (Siyah)",
        "hedef": 0,
        "kaynaklar": [
            {"site": "amazon",    "url": "https://www.amazon.com.tr/dp/B0CN1HK8P5"},
            {"site": "incehesap", "url": "https://www.incehesap.com/msi-mag-pano-m100r-pz-4-argb-fanli-siyah-micro-atx-oyuncu-kasasi-fiyatlari/"},
        ],
    },
    "psu": {
        "isim": "MSI MAG A750GL 750W 80+ Gold PSU",
        "hedef": 0,
        "kaynaklar": [
            {"site": "amazon",      "url": "https://www.amazon.com.tr/dp/B0C79GBL8L"},
            {"site": "hepsiburada", "url": "https://www.hepsiburada.com/msi-mag-a750gl-pcie5-750w-80-gold-full-modueler-guc-kaynagi-pm-HBC00009OVKLS"},
            {"site": "incehesap",   "url": "https://www.incehesap.com/msi-mag-a750gl-pcie5-750w-80-gold-full-moduler-guc-kaynagi-fiyatlari/"},
        ],
    },
    "ssd": {
        "isim": "Kioxia Exceria PRO 1TB NVMe",
        "hedef": 0,
        "kaynaklar": [
            {"site": "hepsiburada", "url": "https://www.hepsiburada.com/kioxia-exceria-pro-lse10z001tg8-1-tb-7300-6400-mb-s-m-2-ssd-disk-pm-HBC0000665247288"},
            {"site": "incehesap",   "url": "https://www.incehesap.com/kioxia-exceria-pro-lse10z001tg8-pci-express-4-0-1-tb-m-2-ssd-fiyatlari/"},
        ],
    },
    "ram": {
        "isim": "Patriot Viper Venom 16GB DDR5 6000 CL30",
        "hedef": 0,
        "kaynaklar": [
            {"site": "incehesap", "url": "https://www.incehesap.com/patriot-viper-venom-pvv516g60c30-16-gb-6000-mhz-cl30-ddr5-ram-fiyatlari/"},
        ],
    },
    "anakart": {
        "isim": "MSI PRO B850M-G AM5 Anakart",
        "hedef": 0,
        "kaynaklar": [
            {"site": "amazon",      "url": "https://www.amazon.com.tr/dp/B0D7Q5KXNK"},
            {"site": "hepsiburada", "url": "https://www.hepsiburada.com/msi-pro-b850m-g-am5-ddr5-8200-oc-mhz-matx-anakart-pm-HBC0000CDBMDX"},
            {"site": "incehesap",   "url": "https://www.incehesap.com/msi-pro-b850m-g-amd-am5-ddr5-micro-atx-anakart-fiyatlari/"},
        ],
    },
    "gpu": {
        "isim": "Sapphire RX 9070 XT Pulse 16GB",
        "hedef": 0,
        "kaynaklar": [
            {"site": "hepsiburada", "url": "https://www.hepsiburada.com/sapphire-rx-9070-xt-pulse-11348-03-20g-256-bit-gddr6-16-gb-ekran-karti-pm-HBC0000879L6A"},
            {"site": "incehesap",   "url": "https://www.incehesap.com/sapphire-rx-9070-xt-pulse-11348-03-20g-256-bit-gddr6-16-gb-ekran-karti-fiyatlari/"},
        ],
    },
    "sogutucu": {
        "isim": "Thermalright Peerless Assassin 120 SE ARGB",
        "hedef": 0,
        "kaynaklar": [
            {"site": "hepsiburada", "url": "https://www.hepsiburada.com/thermalright-peerless-assassin-120-se-argb-siyah-islemci-sogutucu-pm-HBC00009KGJID"},
        ],
    },
    "cpu": {
        "isim": "AMD Ryzen 7 7800X3D",
        "hedef": 0,
        "kaynaklar": [
            {"site": "amazon",      "url": "https://www.amazon.com.tr/dp/B0CJML6LQZ"},
            {"site": "hepsiburada", "url": "https://www.hepsiburada.com/amd-ryzen-7-7800x3d-sekiz-cekirdek-4-2-ghz-islemci-pm-HBC00006BIHVF"},
        ],
    },
}

# ── SCRAPER API İSTEK ────────────────────────────────
def scrape(url: str) -> str | None:
    """ScraperAPI üzerinden sayfa çeker."""
    api_url = "https://api.scraperapi.com/"
    params  = {
        "api_key": SCRAPER_KEY,
        "url":     url,
        "country_code": "tr",
    }
    try:
        r = requests.get(api_url, params=params, timeout=60)
        if r.status_code == 200:
            return r.text
        print(f"    ScraperAPI {r.status_code}: {url[:60]}")
    except Exception as e:
        print(f"    ScraperAPI hata: {e}")
    return None

# ── PARSE ────────────────────────────────────────────
def parse_price(text: str, site: str) -> float | None:
    """Siteden gelen HTML'den fiyat çıkarır."""

    patterns = []

    if site == "amazon":
        patterns = [
            r'"priceAmount"\s*:\s*([\d,\.]+)',
            r'"displayPrice"\s*:\s*"([\d.,]+)\s*TL"',
            r'class="a-price-whole">\s*([\d.,]+)',
            r'id="priceblock_ourprice"[^>]*>\s*([\d.,\s]+)',
        ]
    elif site == "hepsiburada":
        patterns = [
            r'"salePrice"\s*:\s*([\d]+(?:\.\d+)?)',
            r'"price"\s*:\s*([\d]+(?:\.\d+)?)',
            r'"finalPrice"\s*:\s*([\d]+(?:\.\d+)?)',
            r'data-price="([\d]+(?:\.\d+)?)"',
            r'"priceValue"\s*:\s*([\d]+(?:\.\d+)?)',
        ]
    elif site == "incehesap":
        patterns = [
            r'itemprop="price"[^>]*content="([\d.,]+)"',
            r'"price"\s*:\s*"?([\d]+(?:[,\.]\d+)?)"?',
            r'"lowPrice"\s*:\s*"?([\d]+(?:[,\.]\d+)?)"?',
            r'class="[^"]*price[^"]*"[^>]*>([\d.,]+)',
        ]

    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            raw = m.group(1).strip().replace("\xa0", "").replace(" ", "")
            # TR format: "4.661,76" → 4661.76
            if "," in raw and "." in raw:
                raw = raw.replace(".", "").replace(",", ".")
            elif "," in raw:
                parts = raw.split(",")
                if len(parts[-1]) <= 2:
                    raw = raw.replace(",", ".")
                else:
                    raw = raw.replace(",", "")
            elif "." in raw:
                parts = raw.split(".")
                if len(parts[-1]) > 2:
                    raw = raw.replace(".", "")
            try:
                p = float(raw)
                if 100 < p < 500_000:
                    return p
            except:
                continue
    return None

# ── MIN FİYAT ────────────────────────────────────────
def get_min_price(pid, product):
    prices = {}
    for src in product["kaynaklar"]:
        site = src["site"]
        url  = src["url"]
        html = scrape(url)
        if html:
            p = parse_price(html, site)
            if p:
                prices[site] = p
                print(f"    {site:12s} → {p:,.2f} TL")
            else:
                print(f"    {site:12s} → parse edilemedi")
        else:
            print(f"    {site:12s} → sayfa alınamadı")
        time.sleep(3)

    if not prices:
        return None, None
    best = min(prices, key=prices.get)
    return prices[best], best

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
    print("  Fiyat Takip Botu v5  (ScraperAPI proxy)")
    print(f"  {len(PRODUCTS)} ürün  |  {CHECK_INTERVAL//60} dk aralık")
    print("=" * 55)

    if not SCRAPER_KEY:
        print("[UYARI] SCRAPER_KEY tanımlı değil!")

    send_tg(
        "✅ <b>Fiyat Botu v5 başladı!</b>\n"
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
