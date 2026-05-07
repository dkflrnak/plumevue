from flask import Flask, render_template, request, send_file
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from openai import OpenAI

import os
import zipfile
import uuid
import textwrap
import json

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

UPLOAD_FOLDER = "static/uploads"
OUTPUT_FOLDER = "static/generated"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

generated_images_global = []


# ---------------------------------------------------
# FONT SAFE SYSTEM
# ---------------------------------------------------
def get_font(size):

    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]

    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)

    return ImageFont.load_default()


# ---------------------------------------------------
# TEXT BLOCK
# ---------------------------------------------------
def calc_text_block(text, font, wrap_width, line_spacing):

    lines = textwrap.wrap(text, width=wrap_width)

    return lines, len(lines) * line_spacing


def draw_text_block(
    draw,
    text,
    font,
    canvas_width,
    start_y,
    fill,
    wrap_width,
    line_spacing
):

    lines, _ = calc_text_block(
        text,
        font,
        wrap_width,
        line_spacing
    )

    y = start_y

    for line in lines:

        bbox = draw.textbbox((0, 0), line, font=font)

        text_width = bbox[2] - bbox[0]

        x = (canvas_width - text_width) / 2

        # soft shadow
        draw.text(
            (x + 2, y + 2),
            line,
            font=font,
            fill=(0, 0, 0, 120)
        )

        draw.text(
            (x, y),
            line,
            font=font,
            fill=fill
        )

        y += line_spacing

    return y


# ---------------------------------------------------
# HOME
# ---------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def home():

    global generated_images_global

    generated_images = []

    if request.method == "POST":

        topic = request.form["topic"]
        template = request.form["template"]

        uploaded_files = request.files.getlist("images")

        image_paths = []

        for file in uploaded_files:

            if file.filename == "":
                continue

            ext = file.filename.split(".")[-1]

            filename = f"{uuid.uuid4()}.{ext}"

            path = os.path.join(
                UPLOAD_FOLDER,
                filename
            )

            file.save(path)

            image_paths.append(path)

        # ---------------------------------------------------
        # GPT CARD COPY
        # ---------------------------------------------------
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "user",
                    "content": f"""
너는 인스타에서 실제 저장/공유되는
뷰티 카드뉴스 카피라이터

주제: {topic}

구조:
1장 훅
2장 공감
3장 원인
4장 해결
5장 CTA

조건:
- 20대 여성 타겟
- 뷰티 감성
- 짧고 강한 문장
- 감성적인 말투
- 이모티콘 금지
- 반드시 JSON 형식

{{
  "cards":[
    {{
      "title":"...",
      "content":"..."
    }},
    {{
      "title":"...",
      "content":"..."
    }},
    {{
      "title":"...",
      "content":"..."
    }},
    {{
      "title":"...",
      "content":"..."
    }},
    {{
      "title":"...",
      "content":"..."
    }}
  ]
}}
"""
                }
            ]
        )

        content = response.choices[0].message.content

        content = (
            content
            .replace("```json", "")
            .replace("```", "")
        )

        data = json.loads(content)

        cards = data["cards"]

        # ---------------------------------------------------
        # CARD IMAGE LOOP
        # ---------------------------------------------------
        for i, card in enumerate(cards):

            # ---------------------------------------------------
            # BASE IMAGE
            # ---------------------------------------------------
            base = Image.open(
                image_paths[i % len(image_paths)]
            ).convert("RGBA")

            base = base.resize((1080, 1350))

            # 살짝 블러
            blur = base.filter(
                ImageFilter.GaussianBlur(1.2)
            )

            # 어두운 오버레이
            overlay = Image.new(
                "RGBA",
                blur.size,
                (0, 0, 0, 75)
            )

            img = Image.alpha_composite(
                blur,
                overlay
            )

            # ---------------------------------------------------
            # GLASS CARD SYSTEM
            # ---------------------------------------------------
            box_left = 80
            box_top = 760
            box_right = 1000
            box_bottom = 1240

            radius = 55

            # -----------------------------
            # glass blur background
            # -----------------------------
            glass_region = img.crop(
                (
                    box_left,
                    box_top,
                    box_right,
                    box_bottom
                )
            )

            glass_region = glass_region.filter(
                ImageFilter.GaussianBlur(4)
            )

            img.paste(
                glass_region,
                (box_left, box_top)
            )

            # -----------------------------
            # glass layer
            # -----------------------------
            glass_layer = Image.new(
                "RGBA",
                img.size,
                (0, 0, 0, 0)
            )

            glass_draw = ImageDraw.Draw(glass_layer)

            # -----------------------------
            # main glass panel
            # -----------------------------
            glass_draw.rounded_rectangle(
                (
                    box_left,
                    box_top,
                    box_right,
                    box_bottom
                ),
                radius=radius,
                fill=(20, 20, 20, 60),
                outline=(255, 255, 255, 40),
                width=2
            )

            # -----------------------------
            # glossy top line
            # -----------------------------
            glass_draw.rounded_rectangle(
                (
                    box_left + 30,
                    box_top + 20,
                    box_right - 30,
                    box_top + 24
                ),
                radius=30,
                fill=(255, 255, 255, 90)
            )

            # -----------------------------
            # subtle gradient
            # -----------------------------
            for y in range(box_top, box_bottom):

                progress = (
                    y - box_top
                ) / (
                    box_bottom - box_top
                )

                alpha = int(24 * (1 - progress))

                glass_draw.line(
                    [
                        (box_left, y),
                        (box_right, y)
                    ],
                    fill=(255, 255, 255, alpha)
                )

            # -----------------------------
            # composite
            # -----------------------------
            img = Image.alpha_composite(
                img,
                glass_layer
            )

            draw = ImageDraw.Draw(img)

            # ---------------------------------------------------
            # FONT
            # ---------------------------------------------------
            title_font = get_font(68)
            content_font = get_font(38)
            small_font = get_font(26)

            # ---------------------------------------------------
            # TEXT CALC
            # ---------------------------------------------------
            title_lines, title_h = calc_text_block(
                card["title"],
                title_font,
                12,
                70
            )

            content_lines, content_h = calc_text_block(
                card["content"],
                content_font,
                22,
                55
            )

            total_h = (
                title_h +
                content_h +
                40
            )

            start_y = (
                (box_top + box_bottom) / 2
                - total_h / 2
            )

            # ---------------------------------------------------
            # HEADER
            # ---------------------------------------------------
            draw.text(
                (90, 60),
                "@plume_vue",
                font=small_font,
                fill=(255, 255, 255, 220)
            )

            # ---------------------------------------------------
            # TITLE
            # ---------------------------------------------------
            draw_text_block(
                draw,
                card["title"],
                title_font,
                1080,
                start_y,
                (245, 245, 245),
                12,
                70
            )

            # ---------------------------------------------------
            # CONTENT
            # ---------------------------------------------------
            draw_text_block(
                draw,
                card["content"],
                content_font,
                1080,
                start_y + title_h + 40,
                (230, 230, 230),
                22,
                55
            )

            # ---------------------------------------------------
            # FOOTER
            # ---------------------------------------------------
            draw.text(
                (120, 1180),
                "plume vue · beauty notes",
                font=small_font,
                fill=(255, 255, 255, 170)
            )

            draw.text(
                (920, 1180),
                f"{i+1:02} · 05",
                font=small_font,
                fill=(255, 255, 255, 170)
            )

            # ---------------------------------------------------
            # SAVE
            # ---------------------------------------------------
            out_name = f"card_{i+1}.png"

            out_path = os.path.join(
                OUTPUT_FOLDER,
                out_name
            )

            img.save(out_path)

            generated_images.append(
                f"generated/{out_name}"
            )

    generated_images_global = generated_images

    return render_template(
        "index.html",
        generated_images=generated_images
    )


# ---------------------------------------------------
# DOWNLOAD ZIP
# ---------------------------------------------------
@app.route("/download")
def download():

    zip_path = "static/cards.zip"

    with zipfile.ZipFile(zip_path, "w") as z:

        for img in generated_images_global:

            z.write(
                f"static/{img}",
                arcname=os.path.basename(img)
            )

    return send_file(
        zip_path,
        as_attachment=True
    )


# ---------------------------------------------------
# RUN
# ---------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)