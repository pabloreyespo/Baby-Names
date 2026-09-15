# Design

A personal data story in the spirit of Spotify Wrapped, Apple product pages, and an architecture portfolio: cream ground, generous whitespace, one huge number per chapter, soft rounded cards, quiet motion. Light theme only. The personal story is one long free scroll; chapters reveal as they enter and numbers count up once.

## Palette

| token | hex | role |
| --- | --- | --- |
| `--cream` | `#F5EFE3` | page background, inputs |
| `--cream-deep` | `#EDE3D1` | cards (form, charts, discovery tiles) |
| `--burgundy` | `#6B1F2B` | big numbers, eyebrows, buttons, links, primary chart mark |
| `--burgundy-deep` | `#4A121B` | brand, name input, cover and closing numbers, hover |
| `--burgundy-soft` | `#A8626C` | second chart series, tile hover tint |
| `--ink` | `#1E1A17` | headlines |
| `--ink-soft` | `#5C544D` | body text, labels, axis text, third series |
| `--rule` | `#D9CDB9` | hairlines, gridlines |

Chart support colors, only for series that must be told apart (never for UI):

| token | hex | role |
| --- | --- | --- |
| `--teal` | `#1F6F78` | second chart series, hombres in sex splits |
| `--ochre` | `#B0761F` | third chart series |
| `--blue` | `#3C5A8A` | fourth chart series |
| `--plum` | `#7A4E8C` | fifth chart series |

Headlines are ink, body is ink-soft, burgundy is reserved for the number and for interaction. No pure white, no shadows; depth comes from cream-deep cards with 24px radius and a 4px burgundy focus ring on inputs.

## Type

- Display: Ranade 700, sentence case, tracking -0.025em, leading 0.98. Hero title up to 6.5rem, chapter title up to 5rem, big number up to 9rem at leading 0.9 and tracking -0.03em, tabular figures.
- Text: Switzer 400 and 500. Body 1.125rem at 1.55 leading, measure 60ch. Lede up to 1.4rem in ink-soft.
- Eyebrow: Switzer 500, 0.8125rem, tracking 0.04em, burgundy, with a two-digit chapter index in Ranade separated by a hairline.
- Loaded from Fontshare:

```html
<link href="https://api.fontshare.com/v2/css?f[]=ranade@700&f[]=switzer@400,500&display=swap" rel="stylesheet">
```

## Casing and writing

Spanish. Sentence case: first letter of a title or sentence capitalized, proper nouns capitalized (Chile, Registro Civil, INE, comuna names). Never full uppercase words or all-caps labels. No emojis, no em dashes, no exclamation marks. Spanish thousands separator (1.234) and decimal comma. Estimates are labeled "estimación".

## Layout

- Nav: sticky, translucent cream with blur, brand left in Ranade, two links right. One hairline below.
- Home: hero only. Eyebrow, headline, lede, then the form inside one card: the name in display type with an "otro al azar" link, a three-column row for year and comunas, one pill button. A radial-masked topo texture sits behind the hero at low opacity.
- Story: chapters stacked with 6 to 11rem of air between them, no dividers. Each chapter: eyebrow with index, title, text column with the big number above the body, and the chart in a card on the right above 940px (equal weight). Cover and closing numbers use burgundy-deep.
- Share chapter: a square burgundy card (topo texture) with name, year and four numbers, next to Download and Share pill buttons. Download renders the DOM to PNG at 2x; Share uses the Web Share API with the image when supported, otherwise copies the link.
- Discoveries: index is a grid of tall cream-deep tiles (index number, title, summary, date) that lift on hover. Articles are a 900px column with sections spaced 4rem, charts in cards.
- Footer: sources left, estimate disclaimer right.

## Motion

Elements wrapped in `Reveal` fade in and rise 28px over 700 to 900ms with an ease-out curve when 20% visible, once. Big numbers count from zero over 1.4s with cubic ease-out when half visible, keeping any prefix or suffix ("N° ", "%", "1 de "). Buttons lift 1px on hover. `prefers-reduced-motion` disables all of it.

## Textures

- `topo_cream.webp`: hero backdrop, opacity 0.35 under a radial mask.
- `topo_burgundy.webp`: share card background.
- `grain_*.webp`: unused in this theme, kept for later.
Never behind chart data.

## Charts

One Altair theme in `api/app/charts.py`: cream background, no view stroke, dashed hairline gridlines at low opacity, Switzer 11px labels in ink-soft, no ticks, legend on top. Series: burgundy, teal, ochre, blue, plum, ink-soft, in that order, so categories differ by hue and not only by lightness (burgundy against burgundy-soft was unreadable for color blindness). Sex splits use burgundy for mujeres and teal for hombres. Single series charts with a highlight keep burgundy-deep against burgundy-soft, where the contrast is deliberate. The visitor's birth year is a dashed burgundy-deep rule with a label. Width is container, heights 160 to 340. Charts sit inside cream-deep cards so their cream background reads as an inset panel.
