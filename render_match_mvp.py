"""Render the match MVP poster using the fonts from the original PSD design.

Place three font files in assets/fonts/ before running:
    steelfish rg.ttf
    InterTight-Regular.ttf
    Inter_24pt-Regular.ttf
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from player_names import get_official_name

ROOT = Path(__file__).resolve().parent
FONTS = ROOT / 'assets' / 'fonts'
CANVAS_SIZE = (1100, 1100)

STEELFISH = FONTS / 'steelfish rg.ttf'
INTER_TIGHT = FONTS / 'InterTight-Regular.ttf'
INTER = FONTS / 'Inter_24pt-Regular.ttf'
INTER_TIGHT_MEDIUM = FONTS / "InterTight-Medium.ttf"


def _font(path, size):
    if not path.is_file():
        raise FileNotFoundError(
            f'Missing font: {path}\n'
            'Extract the three required fonts from the supplied archive into assets/fonts/.'
        )
    return ImageFont.truetype(str(path), size)


def _fitted_font(draw, text, font_path, size, max_width, min_size=17):
    """Decrease type size only when a nickname or number does not fit."""
    while size > min_size:
        font = _font(font_path, size)
        if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
            return font
        size -= 1
    return _font(font_path, min_size)


def _draw_match_heading(image, match_number):
    """Steelfish display title, filled with the cyan-to-blue ALGS gradient."""
    title = f'MATCH {match_number}'
    font = _font(STEELFISH, 200)
    left, top, right, bottom = font.getbbox(title)
    width, height = right - left, bottom - top

    mask = Image.new('L', (width, height), 0)
    ImageDraw.Draw(mask).text((-left, -top), title, font=font, fill=255)

    gradient = Image.new('RGB', (width, height))
    grad_draw = ImageDraw.Draw(gradient)
    first, last = (93, 220, 232), (78, 103, 243)
    for x in range(width):
        t = x / max(width - 1, 1)
        color = tuple(round((1 - t) * first[i] + t * last[i]) for i in range(3))
        grad_draw.line(((x, 0), (x, height)), fill=color)
    image.paste(gradient, (75, 158), mask)


def render_match_mvp(match_data, template_path, output_path):
    image = Image.open(template_path).convert('RGB')
    if image.size != CANVAS_SIZE:
        raise ValueError(f'Expected template size {CANVAS_SIZE}, got {image.size}')

    draw = ImageDraw.Draw(image)
    number = match_data['match_number']
    players = match_data['top_players'][:3]
    event = match_data.get('event_name', 'ALGS CHAMPIONSHIP 2025')

    draw.text(
        (75, 56), f'{event} - MATCH {number}',
        font=_font(INTER_TIGHT, 27), fill='white', anchor='lt'
    )
    _draw_match_heading(image, number)

    for i, player in enumerate(players):
        y = (440, 632, 822)[i]
        name = get_official_name(str(player['name']), player.get('team'))
        kills = str(player['kills'])
        damage = f"{player['damage']:,}"

        draw.text(
            (153, y + 18), name,
            font=_fitted_font(draw, name, INTER_TIGHT_MEDIUM, 37, 245),
            fill='#101010', anchor='lt'
        )
        draw.text(
            (137, y + 86), kills,
            font=_font(INTER, 36), fill='#101010', anchor='lt'
        )
        draw.text(
            (282, y + 86), damage,
            font=_fitted_font(draw, damage, INTER, 36, 125),
            fill='#101010', anchor='lt'
        )

    # The MATCH MVP footer is already part of the blank PSD-based template.
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)
    return destination
