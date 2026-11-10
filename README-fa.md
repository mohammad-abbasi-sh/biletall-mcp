# biletall-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/biletall-mcp

سرور MCP غیررسمی و **فقط-خواندنی** برای biletall.com، جست‌وجوی بلیط اتوبوس و هواپیما در ترکیه — ارزان‌ترین سفرهای اتوبوس برای هر مسیر (حرکت‌های امروز، شرکت، چیدمان صندلی، ترمینال‌ها، ساعت‌ها، قیمت‌ها)، ارزان‌ترین پروازها (ایرلاین، فرودگاه‌ها + کدهای یاتا، تاریخ‌ها، ساعت‌ها، قیمت‌ها)، آمار قیمت هر مسیر، پرترددترین مسیرها و جست‌وجوی مکان در میان ۱٬۷۲۶ مکان ترکیه و بین‌المللی.

> ساخته‌شده توسط محمد عباسی در چارچوب «کارخانهٔ MCP ترکیه» (خط تولید به سبک سپهر). وابسته به biletall.com نیست.

## برای ایجنت‌های هوش مصنوعی

به پیکربندی MCP client خود اضافه کنید (stdio):

```json
{
  "mcpServers": {
    "biletall": {
      "command": "uvx",
      "args": ["biletall-mcp==0.1.1"]
    }
  }
}
```

یا به‌صورت محلی اجرا کنید: `python -m biletall_mcp.server` (نیازمند `mcp<2` و `curl-cffi`).

## ابزارها

| ابزار | توضیح |
|------|------|
| `biletall_search_locations` | جست‌وجوی مکان با نام — `query` (مثل «Ankara»، «İstanbul»، «Bodrum»)؛ برای هر نتیجه slug، نام ترکی و URL صفحه در biletall.com را برمی‌گرداند (جست‌وجوی آفلاین در فهرست ۱٬۷۲۶ مکانی پلتفرم) |
| `biletall_bus_route` | ارزان‌ترین سفرهای اتوبوس یک مسیر، برای امروز — `from_city` و `to_city` (نام ترکی یا slug، مثل «İstanbul» به «Ankara»)، `limit` بین ۱ تا ۳۰؛ خلاصه (ارزان‌ترین قیمت، تعداد سفر، ارزان‌ترین/فعال‌ترین شرکت، مدت، امتیاز مسیر) + سفرها (شرکت، نوع اتوبوس، شهر و ترمینال مبدأ، شهر و ترمینال مقصد، قیمت به لیر، ساعت حرکت/رسیدن) |
| `biletall_flight_route` | ارزان‌ترین پروازهای یک مسیر — `from_city` و `to_city`، `limit` بین ۱ تا ۱۰؛ خلاصه (ارزان‌ترین قیمت، ارزان‌ترین/فعال‌ترین ایرلاین، تعداد پرواز، مدت، مسافت) + پروازها که هرکدام تاریخ خود (ISO + ترکی)، ایرلاین، فرودگاه‌های مبدأ/مقصد با کد یاتا، ساعت‌ها و قیمت به لیر را دارند |
| `biletall_price_stats` | آمار قیمت یک مسیر اتوبوس (امروز): تعداد، کمترین / میانه / میانگین / بیشترین قیمت بلیط به لیر در میان ۳۰ سفر ارزانِ فهرست‌شده، تعداد شرکت‌ها و ارزان‌ترین قیمت هر شرکت |
| `biletall_popular_routes` | پرترددترین مسیرهای اتوبوس با قیمت: نام مسیر، slug مبدأ/مقصد، ارزان‌ترین قیمت به لیر، URL مسیر؛ `limit` بین ۱ تا ۳۰ |

خروجی نمونه (`biletall_bus_route` / استانبول به آنکارا):

```json
{"from_city": "İstanbul", "to_city": "Ankara", "summary":
 {"cheapest_price_try": 539.0, "journey_count": 719,
  "cheapest_company": "Yeşil Malatya Turizm",
  "most_active_company": "Metro Turizm", "duration": "6s 35dk",
  "route_rating_10": 3.9},
 "count": 2, "journeys": [
  {"company": "Niğde Aydoğanlar", "bus_type": "2+1",
   "origin_city": "İstanbul Avrupa", "origin_station": "Alibeyköy Otogarı",
   "destination_city": "Ankara", "destination_station": "Ankara (Aşti) Otogarı",
   "price_try": 598.0, "departure": "00:19", "arrival": "06:34"}, …]}
```

## چطور کار می‌کند؟

سایت biletall.com (وایت‌لیبل Obilet) صفحات SEO مسیرها را کاملاً سمت سرور تولید می‌کند — بدون ورود، بدون کلید API، بدون کوکی نشست. صفحات مسیر اتوبوس یک جدول خلاصه (ارزان‌ترین بلیط، تعداد سفر، ارزان‌ترین شرکت، مدت، فعال‌ترین شرکت، امتیاز مسیر) با بلوک متای AggregateOffer از schema.org و ۳۰ سفر `<li itemtype="…/BusTrip">` دارند. صفحات مسیر پرواز همان ساختار خلاصه و ۱۰ بلوک ارزان‌ترین پرواز (ایرلاین، تاریخ ترکی، قیمت `data-price`، فرودگاه‌ها + کد یاتا، ساعت‌ها) را دارند. صفحهٔ اصلی ۱۵ مسیر پرتردد را با قیمت دارد. نام شهرها به slug تبدیل می‌شوند (İstanbul → istanbul، Eskişehir → eskisehir؛ «İstanbul Avrupa» → istanbul چون صفحات مسیر شهر پایه را استفاده می‌کنند؛ مکان‌های چندکلمه‌ای با آندرلاین، مثل Antakya Hatay → antakya_hatay). مسیرهای ناشناخته HTTP 404 («Sayfa bulunamadı») برمی‌گردانند که به‌صورت خطای واضح نمایش داده می‌شود. انتقال با جعل TLS کروم (`curl-cffi`، `chrome120`) انجام می‌شود؛ درخواست‌ها با فاصلهٔ حدود ۰٫۸ ثانیه فرستاده می‌شوند؛ همه‌چیز فقط-خواندنی است.

توجه: دو مسیر هم‌خانواده (teknosa.com و hepsiemlak.com) همان روز ساخت این سرور (۲۰۲۶-۱۱-۰۷) پشت چالش جاوااسکریپت Cloudflare رفتند و طبق قوانین کارخانه رد شدند — biletall.com پاسخ تمیز می‌دهد، به همین دلیل این ساخت انتخاب شد.

## نصب

```bash
uvx biletall-mcp==0.1.1        # اجرای مستقیم (نیازمند uv)
# یا
pip install biletall-mcp==0.1.1
biletall-mcp    # سرور MCP را روی stdio راه می‌اندازد
```

## تست‌ها

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

تست‌های آفلاین روی فیکسچرهای ضبط‌شده اجرا می‌شوند (صفحات واقعی، دریافت‌شده در ۲۰۲۶-۱۱-۰۷)؛ تست‌های زنده به biletall.com وصل می‌شوند. در زمان ساخت ۳۴/۳۴ سبز (۲۶ آفلاین + ۸ زنده) به‌علاوهٔ یک تست دودی MCP روی stdio.

## نقشهٔ راه

- جست‌وجوی اتوبوس با تاریخ مشخص (صفحات SEO حرکت‌های امروز را نشان می‌دهند؛ جست‌وجوی تاریخ‌دار به JSON API محافظت‌شده با نشست نیاز دارد)
- صفحات شرکت‌های اتوبوس (`/otobus-firmalari/<slug>`: مسیرها + امتیازهای شرکت)
- جست‌وجوی هتل (سایت بخش Otel دارد)

## مجوز

MIT — نگاه کنید به [LICENSE](LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
