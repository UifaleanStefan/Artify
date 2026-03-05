Copiază aici cele 6 imagini pentru cele 3 slider-e "Vezi transformarea":

- original1.jpg, styled1.jpg  = perechea pentru cardul 1
- original2.jpg, styled2.jpg  = perechea pentru cardul 2
- original3.jpg, styled3.jpg  = perechea pentru cardul 3

Original = poza înainte; styled = portretul artistic după transformare.
Redenumește fișierele tale în original1–3.jpg și styled1–3.jpg.

ALINIERE ÎNAINTE/DUPĂ (pixel la pixel):
- Pagina folosește original1.jpg, original2.png, original3.jpg pentru "înainte" și
  styled1_aligned.jpg, styled2_aligned.jpg, styled3_aligned.jpg pentru "după".
  (Cardurile sunt afișate în ordinea: pair 3, pair 2, pair 1.)
- După ce adaugi sau înlocuiești perechile (originalN, styledN), rulează:
  python scripts/align_demo_pairs.py
  Scriptul creează styledN_aligned.jpg (aliniat la dimensiunile originalului, fără stretch).
- Originalele rămân neschimbate; doar fișierele styled sunt redimensionate/aliniate.
- Recomandat: același raport de aspect pentru toate fișierele (ex: 4:3) pentru container.
