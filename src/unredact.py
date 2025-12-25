import os
import fitz  # PyMuPDF
import glob
import argparse
import sys

def process_file(file_path, output_folder, remove_bbox, highlight_text, custom_name=None):
    """Core logic to process a single PDF file."""
    base_fname = os.path.basename(file_path)
    fname_no_ext = os.path.splitext(base_fname)[0]
    
    # Determine output filename
    if custom_name:
        # Ensure it ends with .pdf
        final_name = custom_name if custom_name.lower().endswith(".pdf") else f"{custom_name}.pdf"
    else:
        final_name = f"{fname_no_ext}_UNREDACTED.pdf"

    print(f"\n[CLEANING] {base_fname} -> {final_name}")
    try:
        doc = fitz.open(file_path)
        new_doc = fitz.open() 
        
        for page in doc:
            new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            
            # --- STEP 1: RESTORE IMAGES ---
            page_images = page.get_images(full=True)
            
            for img in page_images:
                xref = img[0]
                try:
                    img_rects = page.get_image_rects(xref)
                    if not img_rects:
                        continue
                        
                    target_rect = img_rects[0]
                    
                    if target_rect.height > 10:
                        pix = fitz.Pixmap(doc, xref)
                        
                        should_keep = True
                        if remove_bbox == 1:
                            if pix.colorspace.n > 3: 
                                check_pix = fitz.Pixmap(fitz.csRGB, pix)
                            else:
                                check_pix = pix

                            pixels = check_pix.samples
                            avg_brightness = sum(pixels) / len(pixels)
                            
                            if avg_brightness < 15:
                                should_keep = False
                                print(f"  [REMOVED] Black redaction box at {target_rect}")
                            
                            if check_pix != pix: check_pix = None

                        if should_keep:
                            new_page.insert_image(target_rect, pixmap=pix)
                            
                        pix = None 
                        
                except Exception as e:
                    print(f"  [DEBUG] Skipping image xref {xref}: {e}")

        # --- STEP 2: RECOVER DIGITAL TEXT ---
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
                                overlay=True
                            )

        out_path = os.path.join(output_folder, final_name)
        new_doc.save(out_path, garbage=4, deflate=True)
        doc.close()
        new_doc.close()
        print(f"✅ Success: Saved to {out_path}")
        
    except Exception as e:
        print(f"❌ Error processing {base_fname}: {e}")

def run_operation(input_path, output_folder, remove_bbox, highlight_text, custom_name):
    if not os.path.exists(output_folder): 
        os.makedirs(output_folder)

    if os.path.isfile(input_path):
        if input_path.lower().endswith(".pdf"):
            process_file(input_path, output_folder, remove_bbox, highlight_text, custom_name)
        else:
            print("❌ Error: The specified file is not a PDF.")
    elif os.path.isdir(input_path):
        files = glob.glob(os.path.join(input_path, "*.pdf"))
        print(f"Target detected: Directory ({len(files)} PDFs found)")
        for file_path in files:
            # Custom name only applies clearly to single-file mode; 
            # for folders, we stick to the default suffix logic.
            process_file(file_path, output_folder, remove_bbox, highlight_text, None)
    else:
        print(f"❌ Error: Input path '{input_path}' does not exist.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-i", "--input", type=str, help="Input folder or file")
    parser.add_argument("-o", "--output", type=str, help="Output folder")
    parser.add_argument("-n", "--name", type=str, help="Custom output filename (single file mode only)")
    parser.add_argument("-b", "--bbox", type=int, default=1, choices=[0, 1], help="1=remove black boxes, 0=keep")
    parser.add_argument("--highlight", "--hl", type=int, default=1, choices=[0, 1], help="1=red text, 0=black")
    parser.add_argument("-h", "--help", action="store_true", help="Show help")

    args, unknown = parser.parse_known_args()

    if args.help:
        readme_path = os.path.join("..", "docs", "Readme.md")
        if os.path.exists(readme_path):
            with open(readme_path, "r") as f: print(f.read())
        else:
            print(f"Help file not found at {readme_path}")
        sys.exit(0)

    in_path = args.input if args.input else input("Input (File or Folder): ").strip().replace('"', '')
    out_dir = args.output if args.output else input("Output Folder: ").strip().replace('"', '')

    run_operation(in_path, out_dir, args.bbox, args.highlight, args.name)