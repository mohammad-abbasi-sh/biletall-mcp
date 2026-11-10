# biletall-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/biletall-mcp

biletall.com için resmi olmayan **salt okunur** MCP sunucusu — Türkiye'nin otobüs ve uçak bileti araması: herhangi bir güzergâh için en ucuz otobüs seferleri (bugünkü kalkışlar, firma, koltuk düzeni, istasyonlar, saatler, fiyatlar), en ucuz uçuşlar (havayolu, havalimanları + IATA kodları, tarihler, saatler, fiyatlar), güzergâh başına fiyat istatistikleri, en çok seyahat edilen güzergâhlar ve 1.726 Türk ve uluslararası konumda yer araması.

> Mohammad Abbasi tarafından "Turkey MCP factory" (Sepehr tarzı hat) kapsamında geliştirildi. biletall.com ile bağlantısı yoktur.

## Yapay zekâ ajanları için

MCP istemci yapılandırmanıza ekleyin (stdio):

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

Veya yerelde çalıştırın: `python -m biletall_mcp.server` (`mcp<2`, `curl-cffi` gerekir).

## Araçlar

| Araç | Açıklama |
|------|----------|
| `biletall_search_locations` | İsme göre yer arar — `query` ("Ankara", "İstanbul", "Bodrum"); her eşleşme için slug, Türkçe ad ve biletall.com URL'si döner (1.726 konumlu platform envanterinde çevrimdışı arama) |
| `biletall_bus_route` | Bir güzergâh için en ucuz otobüs seferleri, bugün — `from_city`, `to_city` (Türkçe adlar veya slug'lar, örn. "İstanbul" → "Ankara"), `limit` 1..30; özet (en ucuz fiyat, sefer sayısı, en ucuz/en aktif firma, süre, güzergâh puanı) + seferler (firma, otobüs tipi, kalkış şehri + istasyon, varış şehri + istasyon, TL fiyat, kalkış/varış saatleri) döner |
| `biletall_flight_route` | Bir güzergâh için en ucuz uçuşlar — `from_city`, `to_city`, `limit` 1..10; özet (en ucuz fiyat, en ucuz/en aktif havayolu, uçuş sayısı, süre, mesafe) + her biri kendi tarihli (ISO + Türkçe), havayollu, IATA kodlu havalimanlı, saatli ve TL fiyatlı uçuşlar döner |
| `biletall_price_stats` | Bir otobüs güzergâhı için fiyat istatistikleri (bugün): listelenen en ucuz 30 seferde adet, en düşük / ortanca / ortalama / en yüksek bilet fiyatı (TL), firma sayısı ve firma başına en ucuz fiyat |
| `biletall_popular_routes` | Fiyatlarıyla en çok seyahat edilen otobüs güzergâhları: güzergâh adı, kalkış/varış slug'ları, en ucuz fiyat (TL), güzergâh URL'si; `limit` 1..30 |

Örnek çıktı (`biletall_bus_route` / İstanbul → Ankara):

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

## Nasıl çalışır?

biletall.com (bir Obilet beyaz etiketi) SEO güzergâh sayfalarını tamamen sunucu taraflı üretir — giriş yok, API anahtarı yok, oturum çerezi yok. Otobüs güzergâh sayfaları bir özet tablo (en ucuz bilet, sefer sayısı, en ucuz firma, süre, en aktif firma, güzergâh puanı) ve schema.org AggregateOffer meta bloğu ile 30 `<li itemtype="…/BusTrip">` seferi taşır. Uçak güzergâh sayfaları aynı özet yapısını ve 10 en ucuz uçuş bloğunu (havayolu, Türkçe tarih, `data-price` fiyat, IATA kodlu havalimanlar, saatler) taşır. Ana sayfa fiyatlarıyla birlikte en çok seyahat edilen 15 güzergâhı taşır. Şehir adları slug'a çevrilir (İstanbul → istanbul, Eskişehir → eskisehir; güzergâh sayfaları ana şehri kullandığı için "İstanbul Avrupa" → istanbul; çok kelimeli yerlerde alt çizgi kullanılır, örn. Antakya Hatay → antakya_hatay). Bilinmeyen güzergâhlar HTTP 404 ("Sayfa bulunamadı") döner ve açık bir hata olarak yansıtılır. Aktarım Chrome TLS taklidi (`curl-cffi`, `chrome120`) kullanır; istekler ~0,8 sn arayla yapılır; her şey salt okunurdur.

Not: kardeş alanlar (teknosa.com, hepsiemlak.com) bu sunucunun yapıldığı gün (2026-11-07) Cloudflare JS doğrulamasının arkasına geçti ve fabrika kurallarına göre atlandı — biletall.com temiz yanıt verdiği için bu derleme yapıldı.

## Kurulum

```bash
uvx biletall-mcp==0.1.1        # doğrudan çalıştır (uv gerekir)
# veya
pip install biletall-mcp==0.1.1
biletall-mcp    # MCP sunucusunu stdio üzerinde başlatır
```

## Testler

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Çevrimdışı testler kaydedilmiş örneklerle çalışır (gerçek sayfalar 2026-11-07'de alındı); canlı testler biletall.com'a bağlanır. Derleme anında 34/34 yeşil (26 çevrimdışı + 8 canlı) ve bir MCP stdio duman testi.

## Yol haritası

- Tarihe özel otobüs araması (SEO sayfaları bugünkü kalkışları gösterir; tarihli arama oturum korumalı JSON API gerektirir)
- Otobüs firması sayfaları (`/otobus-firmalari/<slug>`: firma güzergâhları + puanları)
- Otel araması (sitede Otel bölümü var)

## Lisans

MIT — bkz. [LICENSE](LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
