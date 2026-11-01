# arent

Dla Mariusza.

Statyczna kopia strony głównej [arent.pl](https://arent.pl/) (WordPress + WooCommerce, motyw Greengrow),
pobrana 2026-11-01 razem ze wszystkimi zasobami (CSS, JS, fonty, obrazy).

## Struktura

- `index.html` – strona główna
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

- Wygląd i zawartość strony głównej są 1:1 z oryginałem, wszystkie zasoby ładowane są lokalnie.
- Linki do podstron (sklep, produkty, artykuły, kontakt), koszyk, wyszukiwarka i newsletter
  wskazują na działający serwis https://arent.pl/ – to funkcje dynamiczne (PHP/baza danych),
  które nie istnieją w wersji statycznej.
- Usunięto skrypty śledzące (Google Analytics, Facebook Pixel, czat Facebooka) oraz
  statystyki popupu, żeby kopia nie zaśmiecała statystyk oryginału.

## Odświeżenie kopii

```bash
python3 -I tools/mirror.py site && python3 -I tools/postprocess.py site
```
