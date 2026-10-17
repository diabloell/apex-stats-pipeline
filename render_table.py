
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


FONT_PATH = "C:/Windows/Fonts/arial.ttf"


def _fitted_font(draw, text, max_width, start_size=28):
    for size in range(start_size, 15, -1):
        font = ImageFont.truetype(FONT_PATH, size)
        if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
            return font
    return ImageFont.truetype(FONT_PATH, 16)


def render_table(standings, kills_by_match, template_path, output_path):
    image = Image.open(template_path).convert("RGB")
    if image.size != (1920, 1080):
        raise ValueError(f"Template must be 1920x1080, got {image.size}")
    draw = ImageDraw.Draw(image)
    score_font = ImageFont.truetype(FONT_PATH, 28)

    for index, (team_name, points) in enumerate(standings[:20]):
        column = index // 10
        row = index % 10
        dx = 831 * column
        y = 328 + 64 * row + 23

        team_font = _fitted_font(draw, team_name, max_width=370)
        kills = sum(kills_by_match[team_name])

        draw.text((255 + dx, y), team_name, font=team_font,
                  fill="white", anchor="lt")
        draw.text((701.5 + dx, y), str(kills), font=score_font,
                  fill="white", anchor="mt")
        draw.text((826 + dx, y), str(points), font=score_font,
                  fill="black", anchor="mt")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path
