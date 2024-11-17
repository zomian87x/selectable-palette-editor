import os
import gradio as gr
from PIL import Image, ImageDraw
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import hsv_to_rgb
import gradio as gr
import io
from PIL import Image

# 必要なフォルダの作成と初期化
def initialize_folders():
    for folder in ["./colors", "./palette",]:
        os.makedirs(folder, exist_ok=True)
        for file in os.listdir(folder):
            file_path = os.path.join(folder, file)
            if os.path.isfile(file_path):
                os.remove(file_path)

initialize_folders()

def create_palette_image(colors, cell_size=50):
    """
    Create an image visualizing the palette.
    """
    palette_width = len(colors)
    palette_image = Image.new("RGB", (palette_width * cell_size, cell_size))
    draw = ImageDraw.Draw(palette_image)
    for i, color in enumerate(colors):
        x0 = i * cell_size
        x1 = x0 + cell_size
        draw.rectangle([x0, 0, x1, cell_size], fill=color)
    return palette_image

def extract_palette(image, num_colors=16):
    """
    Extract a palette of dominant colors from the image.
    """
    image = image.convert("P", palette=Image.ADAPTIVE, colors=num_colors)
    palette = image.getpalette()
    colors = [tuple(palette[i:i+3]) for i in range(0, len(palette), 3)]
    return colors[:num_colors]

def save_palette_image(color, idx, folder="./colors"):
    """
    Save a small image for a selected color.
    """
    image = create_palette_image([color], cell_size=50)
    save_path = os.path.join(folder, f"color_{idx}.png")
    image.save(save_path)
    return save_path

def list_images_in_folder(folder="./colors"):
    """
    List images in the specified folder.
    """
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith((".png", ".jpg", ".jpeg"))]

def merge_color_images(images):
    """
    Merge all color images into a single palette image.
    """
    images = [Image.open(img) for img in images]
    total_width = sum(img.width for img in images)
    max_height = max(img.height for img in images)
    merged_image = Image.new("RGB", (total_width, max_height))
    
    x_offset = 0
    for img in images:
        merged_image.paste(img, (x_offset, 0))
        x_offset += img.width
    
    save_path = "./palette/merged_palette.png"
    merged_image.save(save_path)
    return save_path

def apply_palette(image, palette):
    """
    Reduce the image to use only the colors in the provided palette.
    """
    if isinstance(palette, list):
        # パレットがリスト形式の場合、そのまま使用
        unique_colors = palette
    else:
        # パレットが画像の場合、色を抽出
        palette = palette.convert("RGB")  # 必ずRGB形式に変換
        unique_colors = list(set(palette.getdata()))  # 重複排除

    # カスタムパレットの生成
    flat_palette = [value for color in unique_colors for value in color]
    flat_palette += [0] * (768 - len(flat_palette))  # パレットサイズを768に調整 (256色 * 3)

    # パレット画像を作成して割り当て
    palette_holder = Image.new("P", (1, 1))
    palette_holder.putpalette(flat_palette)

    # 入力画像をパレットに基づいて変換 (ディザリング無効化)
    reduced_image = image.convert("RGB").quantize(palette=palette_holder, dither=0)
    return reduced_image

def process_batch(input_folder, output_folder, palette_input, num_colors):
    """
    Process all images in the input folder and save reduced color images to output folder.
    """
    if not input_folder or not output_folder:
        return "Please specify both input and output folders."
    
    # パレットの抽出
    if palette_input:
        palette = extract_palette(palette_input, num_colors)
    else:
        palette = None  # デフォルトの処理を適用

    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(exist_ok=True)
    
    processed_files = []
    for file in input_path.glob("*"):
        if file.suffix.lower() in ['.png', '.jpg', '.jpeg']:
            try:
                # Load and process image
                img = Image.open(file)
                if palette is None:
                    palette = extract_palette(img, num_colors)
                reduced_img = apply_palette(img, palette)
                
                # Save reduced image
                output_file = output_path / f"reduced_{file.name}"
                reduced_img.save(output_file)
                
                processed_files.append(str(file.name))
            except Exception as e:
                print(f"Error processing {file}: {e}")
    
    if processed_files:
        return f"Processed {len(processed_files)} files: {', '.join(processed_files)}"
    else:
        return "No images found or processed."

def process_palette(input_image, palette_input, num_colors):
    """
    Extract palette and display gallery with smaller images.
    """
    if palette_input:
        palette = extract_palette(palette_input, num_colors)
    else:
        palette = extract_palette(input_image, num_colors)
    
    palette_images = [create_palette_image([color], cell_size=50) for color in palette]
    return palette_images, palette

# Counter to ensure unique file naming
save_index = 0

with gr.Blocks(theme=gr.themes.Base(), title="Selectable Palette Editor") as app:
    
    gr.Markdown("## Image Color Quantizer")
    with gr.Row():
        with gr.Column():
            with gr.Tab("Single Image"):
                input_image = gr.Image(type="pil", label="Input Image")
                palette_input = gr.Image(type="pil", label="Palette Image (Optional)")
                num_colors = gr.Slider(2, 256, value=16, step=1, label="Number of Colors")
                recolor_button = gr.Button("Generate Palette", variant='primary')
            with gr.Tab("Batch Processing"):
                input_folder = gr.Textbox(label="Input Folder Path")
                output_folder = gr.Textbox(label="Output Folder Path")
                palette_input_batch = gr.Image(type="pil", label="Palette Image (Optional)") #batch 用のinput 
                num_colors_batch = gr.Slider(2, 256, value=16, step=1, label="Number of Colors") # batch 用のslider
                batch_process_button = gr.Button("Process Batch", variant='primary')
                batch_output = gr.Textbox(label="Batch Processing Results")
        
        with gr.Column():
            palette_gallery = gr.Gallery(label="Palette Colors", elem_id="palette_gallery", columns=4, allow_preview=False)
            selected_num = gr.Textbox(label="Selected Index", visible=False) #デバッグ用
            save_to_palette = gr.Button("Save to Palette")
            selected_gallery = gr.Gallery(label="Saved Colors", elem_id="saved_gallery", columns=4, allow_preview=False)
            with gr.Row():
                reset_button = gr.Button("Reset Palette")
                merge_button = gr.Button("Merge Saved Colors")
            merged_output = gr.Image(type="filepath", label="Merged Palette Image")
        
        with gr.Column():
            output_image = gr.Image(label="Reduced Color Image")

    palette_state = gr.State([])
    selected_index = gr.State(None)

    # Generate palette and display small images
    def generate_palette(input_image, palette_input, num_colors):
        palette_images, palette = process_palette(input_image, palette_input, num_colors)
        reduced_image = apply_palette(input_image, palette)
        return palette_images, palette, reduced_image

    def add_to_palette(selected_index, palette):
        global save_index
        if selected_index is None or selected_index == "":
            print("No image selected.")
            return list_images_in_folder(folder="./colors")
        
        try:
            index = int(float(selected_index))
            if 0 <= index < len(palette):
                color = palette[index]
                save_palette_image(color, save_index, folder="./colors")
                save_index += 1
                return list_images_in_folder(folder="./colors")
        except (ValueError, IndexError) as e:
            print(f"Error processing index: {e}")
        return list_images_in_folder(folder="./colors")

    def reset_palette():
        for file in os.listdir("./colors"):
            file_path = os.path.join("./colors", file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        return [], None

    def merge_saved_images():
        images = list_images_in_folder(folder="./colors")
        merged_image_path = merge_color_images(images)
        return merged_image_path

    def update_selected_index(evt: gr.SelectData):
        return str(evt.index)

    # Event handlers
    recolor_button.click(
        generate_palette,
        inputs=[input_image, palette_input, num_colors],
        outputs=[palette_gallery, palette_state, output_image]
    )

    # 修正された batch_process_button のイベントハンドラ
    batch_process_button.click(
        process_batch,
        inputs=[input_folder, output_folder, palette_input_batch, num_colors_batch],
        outputs=batch_output
    )

    palette_gallery.select(
        update_selected_index,
        inputs=[],
        outputs=selected_num
    )

    save_to_palette.click(
        add_to_palette,
        inputs=[selected_num, palette_state],
        outputs=selected_gallery
    )

    reset_button.click(
        reset_palette,
        outputs=[selected_gallery, merged_output]
    )

    merge_button.click(
        merge_saved_images,
        outputs=merged_output
    )

    merge_button.click(
        list_images_in_folder,
        outputs=selected_gallery
    )

app.launch(share=True)