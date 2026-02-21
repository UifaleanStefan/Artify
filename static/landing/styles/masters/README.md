# Pack: You, Painted by the Masters

Place the **15 style reference images** for this pack in this folder.

## File names (required)

Use these exact names so the app can find them:

- `masters-01.jpg` — style 1 (preview)
- `masters-02.jpg` — style 2 (preview)
- `masters-03.jpg` — style 3 (preview)
- `masters-04.jpg` — style 4 (preview)
- `masters-05.jpg` — style 5 (preview)
- `masters-06.jpg` — style 6
- `masters-07.jpg` — style 7
- `masters-08.jpg` — style 8
- `masters-09.jpg` — style 9
- `masters-10.jpg` — style 10
- `masters-11.jpg` — style 11
- `masters-12.jpg` — style 12
- `masters-13.jpg` — style 13
- `masters-14.jpg` — style 14
- `masters-15.jpg` — style 15

**First 5** = available for preview in the gallery. **All 15** are used by the API for style transfer when the user selects that style.

## Format

- JPG (or JPEG) recommended; PNG also works.
- These images are the **reference artwork** the API uses to transfer style onto the user’s photo. Use clear, representative artwork for each master style.

## Where they are used

- **Gallery**: preview styles (1–5) show the image in the style card.
- **API**: when a user picks a style, the corresponding image URL is sent with the user’s photo to the style-transfer API.

Images are served from `/static/landing/styles/masters/` and must be publicly reachable so the API can fetch them (the backend turns relative paths into full URLs using `PUBLIC_BASE_URL`).
