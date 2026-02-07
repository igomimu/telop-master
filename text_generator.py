import argparse
from PIL import Image, ImageDraw, ImageFont
import os
import sys

# Configuration
# Configuration
# output directory
OUTPUT_DIR = "/mnt/c/Users/lucky/Desktop/Ichigo_Assets"
# font path
FONT_PATH = "/mnt/c/Windows/Fonts/msgothic.ttc"

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def generate_text_image(text, color_style="red", simulated_bold=True):
    ensure_dir(OUTPUT_DIR)
    
    # Colors
    if color_style == "red":
        text_color = (200, 0, 0, 255)   # Deep Red
    elif color_style == "black":
        text_color = (0, 0, 0, 255)     # Black
    else:
        text_color = (0, 0, 200, 255)   # Blue (optional)
        
    outline_color = (255, 255, 255, 255) # White

    # Font sizing
    font_size = 150
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except:
        # print("Warning: Custom font not found, utilizing default.") # Reduce noise
        font = ImageFont.load_default()

    # Dummy draw to calculate size
    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_w = right - left
    text_h = bottom - top
    
    # Padding settings
    padding = 40
    stroke_width_outline = 15  # Outer white stroke
    stroke_width_bold = 4      # Inner stroke to simulate bold
    
    # Canvas size
    width = text_w + (padding * 2) + (stroke_width_outline * 2)
    height = text_h + (padding * 2) + (stroke_width_outline * 2)
    
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Position
    x = (width - text_w) / 2
    y = (height - text_h) / 2 - top # Adjust for vertical alignment

    # 1. Draw Outline (White)
    total_outline_stroke = stroke_width_outline + stroke_width_bold
    draw.text((x, y), text, font=font, fill=outline_color, stroke_width=total_outline_stroke, stroke_fill=outline_color)

    # 2. Draw Text (Color)
    if simulated_bold:
        draw.text((x, y), text, font=font, fill=text_color, stroke_width=stroke_width_bold, stroke_fill=text_color)
    else:
        draw.text((x, y), text, font=font, fill=text_color)

    # Save
    safe_text = "".join(c for c in text if c.isalnum() or c in (' ', '_', '-'))[:20]
    filename = f"text_{color_style}_{safe_text}.png"
    output_path = os.path.join(OUTPUT_DIR, filename)
    img.save(output_path)
    print(f"Generated: {output_path}")
    return output_path

def interactive_mode():
    print(f"--- Video Text Generator ---")
    print(f"Output Directory: {OUTPUT_DIR}")
    print("Type text and press Enter to generate.")
    print("Type 'q' to quit.")
    print("----------------------------")
    
    while True:
        try:
            user_input = input("\nText > ")
            if user_input.lower() == 'q':
                break
            if not user_input.strip():
                continue
                
            # Quick color switch? maybe later. Default red.
            color = "red" 
            # Check if user typed "text : black" format
            if ":" in user_input:
                parts = user_input.split(":")
                text_content = parts[0].strip()
                color_arg = parts[1].strip().lower()
                if color_arg in ["red", "black", "blue"]:
                    color = color_arg
            else:
                text_content = user_input
                
            generate_text_image(text_content, color)
            
        except KeyboardInterrupt:
            break
    print("Bye!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate text assets for video.")
    parser.add_argument("text", nargs="?", help="The text to generate. If omitted, enters interactive mode.")
    parser.add_argument("style", nargs="?", default="red", choices=["red", "black", "blue"], help="Color style")
    parser.add_argument("--font", help="Path to a custom font file", default=None)
    
    args = parser.parse_args()
    
    # Override global FONT_PATH if argument is provided
    if args.font:
        if os.path.exists(args.font):
            FONT_PATH = args.font
        else:
            print(f"Error: Font file not found: {args.font}")
            sys.exit(1)

    if args.text:
        generate_text_image(args.text, args.style)
    else:
        interactive_mode()
