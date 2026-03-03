Copiază aici cele 6 imagini pentru cele 3 slider-e "Vezi transformarea":

- original1.jpg, styled1.jpg  = perechea pentru cardul 1
- original2.jpg, styled2.jpg  = perechea pentru cardul 2
- original3.jpg, styled3.jpg  = perechea pentru cardul 3

Original = poza înainte; styled = portretul artistic după transformare.
Redenumește fișierele tale în original1–3.jpg și styled1–3.jpg.

ALINIERE ÎNAINTE/DUPĂ (pixel la pixel):
- Pagina folosește original1_aligned.jpg, original2_aligned.jpg, original3_aligned.jpg pentru
  "înainte". Aceste fișiere sunt generate din originale prin decupare la centru la aceleași
  dimensiuni ca imaginile styled, astfel încât înainte și după să arate aceeași regiune.
- După ce adaugi sau înlocuiești perechile (originalN.jpg, styledN.jpg), rulează:
  python scripts/align_demo_pairs.py
  Scriptul creează originalN_aligned.jpg pentru fiecare pereche (necesită Pillow: pip install Pillow).
- Imaginea "styled" ar trebui să fie rezultatul transferului de stil aplicat pe "original";
  scriptul de aliniere presupune că styled arată regiunea din centrul originalului (zoom la centru).
- Recomandat: același raport de aspect pentru toate cele 6 fișiere (ex: 4:3) pentru a se potrivi
  cu containerul de pe pagină.
