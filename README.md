# arent

Dla Mariusza.

Statyczna kopia serwisu [arent.pl](https://arent.pl/) (WordPress + WooCommerce, motyw Greengrow),
pobrana 2026-11-01: 412 stron – strona główna, sklep, kategorie (z paginacją), produkty,
artykuły, opisy gatunkowe i strony informacyjne.

- Strona główna ma wszystkie zasoby lokalnie, łącznie ze zdjęciami.
- Podstrony zawierają tylko tekst (HTML) oraz potrzebne style, skrypty i fonty –
  **zdjęcia nie są kopiowane**, obrazki na podstronach ładują się z https://arent.pl/.
- Linki między skopiowanymi stronami prowadzą do lokalnych plików.

## Struktura

- `index.html` – strona główna, `*/index.html` – podstrony (ścieżki jak w oryginale, np. `produkt/poecilotheria-vittata/`)
- `wp-content/`, `wp-includes/` – style, skrypty i obrazy z WordPressa (ścieżki jak na serwerze)
- `assets/fonts.googleapis.com`, `assets/fonts.gstatic.com` – lokalne kopie fontów Google
- `tools/` – skrypty, którymi wykonano kopię (do ponownego pobrania)

## Podgląd lokalnie

```bash
python3 -m http.server 8000
```

Następnie otwórz http://localhost:8000/.

Strona działa też na GitHub Pages (plik `.nojekyll` wyłącza przetwarzanie Jekyll).

## Co działa, a co nie

- Wygląd i treść stron są 1:1 z oryginałem.
- Koszyk, „Dodaj do koszyka”, konto, wyszukiwarka, formularz kontaktowy i newsletter
  wskazują na działający serwis https://arent.pl/ – to funkcje dynamiczne (PHP/baza danych),
  które nie istnieją w wersji statycznej. Strony tagów produktów nie zostały skopiowane.
- Usunięto skrypty śledzące (Google Analytics, Facebook Pixel, czat Facebooka) oraz
  statystyki popupu, żeby kopia nie zaśmiecała statystyk oryginału.

## Odświeżenie kopii

`urls.txt` to lista adresów (np. z mapy strony `https://arent.pl/sitemap_index.xml`):

```bash
python3 -I tools/fetchpages.py crawl urls.txt && python3 -I tools/build.py . crawl
```
