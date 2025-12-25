# PDF Redaction Auditor (Unredactor)
This script is designed to process PDF files to relveal what's under weak redaction methods by recoloring digital text and selectively removing black redaction boxes.   
It works by creating a new document and re-inserting only the essential elements from the original.  

## Features
* **Text Recovery:** Extracts underlying digital text that might be hidden beneath redaction layers.  
* **Smart Box Removal:** Detects images that appear to be black redaction boxes (based on brightness) and allows for their removal.  
* **Highlighting:** Option to turn recovered text red to make it easily identifiable.  
* **Batch Processing:** Supports individual files or entire directories.  
  
## Installation  

1. **Install Python 3.x**  
Install Python  
2. **Install Dependencies:**  
   ```bash
   python -m venv venv  
   .\venv\Scripts\Activate  
   pip install -r .\docs\requirements.txt  
   ```


## Usage:  
You can run the script using command-line arguments or by following the interactive prompts.    
Command Line Arguments:    
```bash
python main.py -i <input_path> -o <output_folder> [options]
```
Argument Description:   
-i, --input: to the input PDF file or a folder containing PDFs.  
-o, --output: to the folder where processed files will be saved.  
-n, --name: Custom name for the output file (Single file mode only).  
-b, --bbox1 to remove black box images that aren't flattened on the pdf (default), 0 to keep them.  --hl, --highlight1 to turn recovered text red (default), 0 for black.  
-h, --help: Shows the contents  of this README.Example  
  
To process a folder and turn off the red highlighting:  
```bash
cd <project folder>  
.\venv\Scripts\Activate  
python unredact.py -i ./input_pdfs -o ./cleaned_pdfs --hl 0  
``

Directory Structure:  
├── src  
|   └──unredact.py   
└── docs/  
    └── Readme.md  
    └── requirements.txt  
---  

### 2. requirements.txt  

```text
pymupdf==1.23.26
``
</pre>
