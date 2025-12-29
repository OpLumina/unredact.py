import os
import fitz  # PyMuPDF
import glob
import argparse
import sys
import csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

def clean_vector_redactions(page):
    cleaned_drawings = []
    black_v_removed = 0
    white_v_removed = 0
    drawings = page.get_drawings()
    
    for path in drawings:
        is_redaction = False
        fill_color = path.get("fill")
        stroke_color = path.get("color")
        
        if fill_color:
            if all(c < 0.05 for c in fill_color):
                bbox = path["rect"]
                if bbox.width > 5 and bbox.height > 5:
                    is_redaction = True
                    black_v_removed += 1
        
        if not is_redaction and stroke_color:
            if all(c < 0.05 for c in stroke_color) and path.get("width", 0) > 10:
                is_redaction = True
                black_v_removed += 1

        if not is_redaction and fill_color:
            if all(c > 0.95 for c in fill_color):
                bbox = path["rect"]
                if bbox.width > 5 and bbox.height > 5:
                    is_redaction = True
                    white_v_removed += 1

        if not is_redaction:
            cleaned_drawings.append(path)
            
    return cleaned_drawings, black_v_removed, white_v_removed

def process_file(file_path, output_folder, remove_bbox, highlight_text, custom_name=None):
    base_fname = os.path.basename(file_path)
    fname_no_ext = os.path.splitext(base_fname)[0]
    
    if custom_name:
        final_name = custom_name if custom_name.lower().endswith(".pdf") else f"{custom_name}.pdf"
    else:
        final_name = f"{fname_no_ext}_UNREDACTED.pdf"

    stats = {"black_img": 0, "white_img": 0, "black_vec": 0, "white_vec": 0, "annots": 0}

    print(f"\n[STARTING] {base_fname} -> {final_name}")
    try:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        new_doc = fitz.open() 
        
        for page_index, page in enumerate(doc):
            current_pg = page_index + 1
            print(f"  [PROCESSING] Page {current_pg} of {total_pages}...", end='\r')
            
            page.set_cropbox(page.rect)
            page.set_mediabox(page.rect)

            if remove_bbox == 1:
                page_annots = list(page.annots())
                stats["annots"] += len(page_annots)
                for annot in page_annots:
                    page.delete_annot(annot)

            new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            
            page_images = page.get_images(full=True)
            for img in page_images:
                xref = img[0]
                try:
                    img_rects = page.get_image_rects(xref)
                    if not img_rects: continue
                    target_rect = img_rects[0]
                    
                    if target_rect.height > 10:
                        pix = fitz.Pixmap(doc, xref)
                        should_keep = True
                        if remove_bbox == 1:
                            check_pix = fitz.Pixmap(fitz.csRGB, pix) if pix.colorspace.n > 3 else pix
                            pixels = check_pix.samples
                            avg_brightness = sum(pixels) / len(pixels)
                            
                            if avg_brightness < 15:
                                should_keep = False
                                stats["black_img"] += 1
                            if avg_brightness > 240:
                                should_keep = False
                                stats["white_img"] += 1
                            if check_pix != pix: check_pix = None

                        if should_keep:
                            new_page.insert_image(target_rect, pixmap=pix)
                        pix = None 
                except: continue

            if remove_bbox == 1:
                safe_drawings, b_rem, w_rem = clean_vector_redactions(page)
                stats["black_vec"] += b_rem
                stats["white_vec"] += w_rem
                shape = new_page.new_shape()
                for path in safe_drawings:
                    for item in path["items"]:
                        if item[0] == "l": shape.draw_line(item[1], item[2])
                        elif item[0] == "re": shape.draw_rect(item[1])
                        elif item[0] == "qu": shape.draw_quad(item[1])
                        elif item[0] == "c": shape.draw_bezier(item[1], item[2], item[3], item[4])
                    shape.finish(
                        fill=path.get("fill"), 
                        color=path.get("color"), 
                        width=path.get("width", 1),
                        fill_opacity=path.get("fill_opacity", 1)
                    )
                shape.commit()
            else:
                shape = new_page.new_shape()
                for path in page.get_drawings():
                    for item in path["items"]:
                        if item[0] == "l": shape.draw_line(item[1], item[2])
                        elif item[0] == "re": shape.draw_rect(item[1])
                    shape.finish(fill=path.get("fill"), color=path.get("color"))
                shape.commit()

            text_dict = page.get_text("dict")
            for block in text_dict["blocks"]:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if span["text"].strip():
                            text_color = (1, 0, 0) if highlight_text == 1 else (0, 0, 0)
                            new_page.insert_text(
                                span["origin"], 
                                span["text"], 
                                fontsize=span["size"], 
                                color=text_color,
                                overlay=True,
                                render_mode=0,
                                fill_opacity=1.0
                            )

        summary = (f"\n  [SUMMARY] Removed: {stats['black_img']} BlackImg, {stats['white_img']} WhiteImg, "
                   f"{stats['black_vec']} BlackVec, {stats['white_vec']} WhiteVec, {stats['annots']} Annots")
        print(summary)
        out_path = os.path.join(output_folder, final_name)
        new_doc.save(out_path, garbage=3, deflate=False)
        doc.close()
        new_doc.close()
        print(f"✅ Success: Saved to {out_path}")
        
        return [base_fname, stats['black_img'], stats['white_img'], stats['black_vec'], stats['white_vec'], stats['annots']]
        
    except Exception as e:
        print(f"\n❌ Error processing {base_fname}: {e}")
        return None

def run_operation(input_path, output_folder, remove_bbox, highlight_text, custom_name):
    if not os.path.exists(output_folder): 
        os.makedirs(output_folder)
    
    log_data = []
    
    if os.path.isfile(input_path):
        result = process_file(input_path, output_folder, remove_bbox, highlight_text, custom_name)
        if result: log_data.append(result)
    elif os.path.isdir(input_path):
        files = glob.glob(os.path.join(input_path, "*.pdf"))
        for file_path in files:
            result = process_file(file_path, output_folder, remove_bbox, highlight_text, None)
            if result: log_data.append(result)
    
    if log_data:
        csv_path = os.path.join(output_folder, "summary_of_changes.csv")
        headers = ["Filename", "Black_Images", "White_Images", "Black_Vectors", "White_Vectors", "Annotations"]
        with open(csv_path, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(log_data)
        print(f"\n📊 Summary CSV saved to: {csv_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-i", "--input", type=str)
    parser.add_argument("-o", "--output", type=str)
    parser.add_argument("-n", "--name", type=str)
    parser.add_argument("-b", "--bbox", type=int, default=1)
    parser.add_argument("--highlight", "--hl", type=int, default=1)
    args, unknown = parser.parse_known_args()

    in_path = (args.input if args.input else input("Input Path: ")).strip().replace('"', '')
    out_dir = (args.output if args.output else input("Output Folder: ")).strip().replace('"', '')
    run_operation(in_path, out_dir, args.bbox, args.highlight, args.name)
