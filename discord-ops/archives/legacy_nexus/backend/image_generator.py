import io
import logging

from PIL import Image, ImageDraw, ImageFont

from .killfeed import CombatEventType, ParsedCombatEvent

log = logging.getLogger("dayz-discord-ops.image_generator")


class ImageGenerator:
    """Generates premium visual 'Kill Cards' for combat events."""

    def __init__(self, font_path: str = "/usr/share/fonts/adwaita-mono-fonts/AdwaitaMono-Bold.ttf"):
        self.font_path = font_path
        self._font_cache = {}

        # Color Palette (Dark/Neon "2025" Theme)
        self.colors = {
            "bg_dark": (15, 15, 20),
            "bg_gradient_killer": (40, 10, 10),  # Reddish tint
            "bg_gradient_victim": (10, 10, 40),  # Blueish tint
            "text_white": (240, 240, 240),
            "text_gray": (150, 150, 160),
            "accent_kill": (255, 60, 60),  # Red
            "accent_headshot": (255, 180, 0),  # Gold
            "accent_normal": (60, 200, 255),  # Cyan
            "border": (40, 40, 50),
        }

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        if size not in self._font_cache:
            try:
                self._font_cache[size] = ImageFont.truetype(self.font_path, size)
            except OSError:
                log.warning(f"Could not load font {self.font_path}, falling back to default")
                self._font_cache[size] = ImageFont.load_default()
        return self._font_cache[size]

    def generate_kill_card(self, event: ParsedCombatEvent, location_name: str = "Unknown Location") -> bytes:
        """
        Generates a kill card image for the given event.
        Returns the image bytes (PNG).
        """
        width, height = 800, 200
        image = Image.new("RGB", (width, height), self.colors["bg_dark"])
        draw = ImageDraw.Draw(image)

        # 1. Background Effects (Subtle Gradients)
        # Killer side (Left) - Red tint
        self._draw_gradient_rect(
            draw, 0, 0, width // 2, height, self.colors["bg_gradient_killer"], self.colors["bg_dark"]
        )
        # Victim side (Right) - Blue tint (or reverse based on who died)

        # 2. Border
        draw.rectangle([(0, 0), (width - 1, height - 1)], outline=self.colors["border"], width=2)

        # 3. Main Text Layout
        # Center VS / Weapon Icon area
        center_x = width // 2

        # Event Type & Weapon (Center Top)
        weapon_text = event.weapon if event.weapon else "Unknown Weapon"
        if event.distance_m and event.distance_m > 0:
            weapon_text += f" ({event.distance_m:.0f}m)"

        font_small = self._get_font(16)
        self._get_font(24)
        font_large = self._get_font(32)
        font_huge = self._get_font(40)

        # Draw "VS" or Event Icon
        vs_text = "⚔️"
        if event.is_headshot():
            vs_text = "🎯"
        elif event.event_type == CombatEventType.EXPLOSION_DEATH:
            vs_text = "💥"
        elif event.event_type == CombatEventType.VEHICLE_DEATH:
            vs_text = "🚗"

        draw.text((center_x, height // 2 - 20), vs_text, font=font_huge, fill=self.colors["text_white"], anchor="mm")
        draw.text(
            (center_x, height // 2 + 20),
            weapon_text,
            font=font_small,
            fill=self.colors["text_gray"],
            anchor="mm",
        )

        # 4. Killer Info (Left)
        killer_name = event.killer_name if event.killer_name else "Environment"
        killer_color = self.colors["accent_kill"] if event.is_pvp() else self.colors["text_gray"]

        draw.text((center_x - 100, height // 2 - 10), killer_name, font=font_large, fill=killer_color, anchor="rm")
        # Killer Stats placeholder (e.g. Health?)
        # draw.text((center_x - 100, height//2 + 20), "HP: 100", font=font_small, fill=self.colors["text_gray"], anchor="rm")

        # 5. Victim Info (Right)
        victim_name = event.victim_name
        victim_color = self.colors["text_white"]

        draw.text((center_x + 100, height // 2 - 10), victim_name, font=font_large, fill=victim_color, anchor="lm")
        if event.victim_hp is not None:
            draw.text(
                (center_x + 100, height // 2 + 20),
                f"HP: {event.victim_hp:.0f}",
                font=font_small,
                fill=self.colors["text_gray"],
                anchor="lm",
            )

        # 6. Metadata Stamps (Top/Bottom corners)
        # Location (Bottom Left)
        draw.text((20, height - 30), f"📍 {location_name}", font=font_small, fill=self.colors["text_gray"])

        # Timestamp (Bottom Right)
        draw.text(
            (width - 20, height - 30),
            event.timestamp,
            font=font_small,
            fill=self.colors["text_gray"],
            anchor="ra",
        )

        # Headshot Stamp (Top Right)
        if event.is_headshot():
            self._draw_stamp(image, width - 100, 40, "HEADSHOT", self.colors["accent_headshot"])

        # 7. Convert to Bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format="PNG")
        return img_byte_arr.getvalue()

    def _draw_gradient_rect(self, draw, x, y, w, h, color1, color2):
        """Simulates a horizontal gradient (simple interpolation)"""
        # For simplicity in PIL without numpy, just draw a solid rect for now or simple lines
        # Drawing 50 lines is fast enough
        steps = 50
        for i in range(steps):
            ratio = i / steps
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)

            x_start = int(x + (w * (i / steps)))
            x_end = int(x + (w * ((i + 1) / steps)))

            draw.rectangle([x_start, y, x_end, y + h], fill=(r, g, b))

    def _draw_stamp(self, image, x, y, text, color):
        """Draws a rotated stamp like 'HEADSHOT'"""
        # Create a separate image for the stamp to rotate it
        stamp_img = Image.new("RGBA", (200, 50), (0, 0, 0, 0))
        d = ImageDraw.Draw(stamp_img)
        font = self._get_font(24)

        # Text with border
        d.text((100, 25), text, font=font, fill=color, anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))

        # Rotate
        rotated = stamp_img.rotate(15, expand=1)

        # Paste
        image.paste(rotated, (x - 100, y - 25), rotated)

    def generate_status_card(self, title: str, status_text: str, subtitle: str | None = None) -> bytes:
        """Generates a premium status announcement card (e.g. Server Online)."""
        width, height = 800, 300
        image = Image.new("RGB", (width, height), self.colors["bg_dark"])
        draw = ImageDraw.Draw(image)

        # 1. Background Gradient/Aesthetic
        # Use a dynamic color based on status
        base_color = self.colors["accent_normal"]
        if "online" in status_text.lower() or "up" in status_text.lower():
            base_color = (60, 255, 60)  # Green
        elif "offline" in status_text.lower() or "down" in status_text.lower():
            base_color = (255, 60, 60)  # Red
        elif "update" in status_text.lower() or "applied" in status_text.lower():
            base_color = (255, 180, 0)  # Gold

        self._draw_gradient_rect(draw, 0, 0, width, height, base_color, self.colors["bg_dark"])

        # 2. Border
        draw.rectangle([(0, 0), (width - 1, height - 1)], outline=self.colors["border"], width=4)

        # 3. Text
        font_huge = self._get_font(48)
        font_large = self._get_font(36)
        font_med = self._get_font(24)
        self._get_font(18)

        draw.text((width // 2, 80), title.upper(), font=font_huge, fill=self.colors["text_white"], anchor="mm")
        draw.text((width // 2, 160), status_text, font=font_large, fill=self.colors["text_white"], anchor="mm")

        if subtitle:
            # Wrap subtitle or just draw it
            draw.text((width // 2, 230), subtitle, font=font_med, fill=self.colors["text_gray"], anchor="mm")

        # 4. Corner "Stamps" or icons could be added here

        # 5. Convert to Bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format="PNG")
        return img_byte_arr.getvalue()


# Global Manager
_image_generator: ImageGenerator | None = None


def get_image_generator() -> ImageGenerator:
    global _image_generator
    if _image_generator is None:
        _image_generator = ImageGenerator()
    return _image_generator
