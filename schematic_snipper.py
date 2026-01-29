import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import json
import os

class SchematicSnipper:
    def __init__(self, root):
        self.root = root
        self.root.title("Schematic Snipper - Pro Troubleshooter")
        self.root.geometry("1500x900")
        
        # Variables
        self.doc = None
        self.pdf_path = ""
        self.zoom = 2.0
        self.snippets_data = []
        self.page_images = []  
        self.page_offsets = [] 
        
        self.setup_ui()

    def setup_ui(self):
        # --- Toolbar ---
        self.toolbar = tk.Frame(self.root, bg="#2c3e50", pady=5)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        
        # File Operations
        tk.Button(self.toolbar, text="📂 Open PDF", command=self.open_pdf, bg="#ecf0f1").pack(side=tk.LEFT, padx=5)
        tk.Button(self.toolbar, text="💾 Save Workspace", command=self.save_workspace, bg="#27ae60", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(self.toolbar, text="📂 Load Workspace", command=self.load_workspace, bg="#2980b9", fg="white").pack(side=tk.LEFT, padx=5)
        
        tk.Frame(self.toolbar, width=2, bg="gray").pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Snip Size Control
        tk.Label(self.toolbar, text="Snip Size (px):", fg="white", bg="#2c3e50").pack(side=tk.LEFT, padx=5)
        self.size_var = tk.StringVar(value="600")
        tk.Entry(self.toolbar, textvariable=self.size_var, width=5).pack(side=tk.LEFT, padx=5)
        
        # Progress Bar (Hidden by default)
        self.progress = ttk.Progressbar(self.toolbar, orient=tk.HORIZONTAL, length=200, mode='determinate')
        self.progress.pack(side=tk.RIGHT, padx=10)
        self.progress.pack_forget() 

        self.status_label = tk.Label(self.toolbar, text="No PDF Loaded", fg="white", bg="#2c3e50", font=("Arial", 10))
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # --- Main View ---
        self.paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=6, bg="#444")
        self.paned.pack(fill=tk.BOTH, expand=True)

        # PDF View
        self.pdf_container = tk.Frame(self.paned)
        self.paned.add(self.pdf_container, stretch="always")
        
        self.v_scroll = tk.Scrollbar(self.pdf_container)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scroll = tk.Scrollbar(self.pdf_container, orient=tk.HORIZONTAL)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.pdf_canvas = tk.Canvas(self.pdf_container, bg="#333", 
                                    xscrollcommand=self.h_scroll.set, 
                                    yscrollcommand=self.v_scroll.set)
        self.pdf_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.v_scroll.config(command=self.pdf_canvas.yview)
        self.h_scroll.config(command=self.pdf_canvas.xview)

        self.setup_sidebar()

        self.pdf_canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.pdf_canvas.bind("<B1-Motion>", self.on_move_press)
        self.pdf_canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.pdf_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def setup_sidebar(self):
        self.snip_container = tk.Frame(self.paned, width=650, bg="#dcdde1")
        self.paned.add(self.snip_container, stretch="never")
        self.snip_canvas = tk.Canvas(self.snip_container, bg="#dcdde1", width=630)
        self.snip_scroll = tk.Scrollbar(self.snip_container, orient=tk.VERTICAL, command=self.snip_canvas.yview)
        self.snip_list_frame = tk.Frame(self.snip_canvas, bg="#dcdde1")
        self.snip_canvas.create_window((0, 0), window=self.snip_list_frame, anchor="nw")
        self.snip_canvas.configure(yscrollcommand=self.snip_scroll.set)
        self.snip_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.snip_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.snip_list_frame.bind("<Configure>", lambda e: self.snip_canvas.configure(scrollregion=self.snip_canvas.bbox("all")))

    def open_pdf(self, path=None):
        if not path:
            path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.pdf_path = path
            self.doc = fitz.open(path)
            self.render_all_pages()

    def render_all_pages(self):
        self.pdf_canvas.delete("all")
        self.page_images = []
        self.page_offsets = []
        current_y = 0
        max_w = 0

        # Show Progress Bar
        total_pages = len(self.doc)
        self.progress.pack(side=tk.RIGHT, padx=10)
        self.progress['maximum'] = total_pages
        self.status_label.config(text="Rendering Pages...")

        for i, page in enumerate(self.doc):
            pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            tk_img = ImageTk.PhotoImage(img)
            
            self.page_offsets.append((current_y, current_y + pix.height))
            self.pdf_canvas.create_image(0, current_y, anchor=tk.NW, image=tk_img)
            self.page_images.append(tk_img)
            
            current_y += pix.height + 20
            if pix.width > max_w: max_w = pix.width
            
            # Update Progress
            self.progress['value'] = i + 1
            self.root.update_idletasks() # Refresh UI so it doesn't hang

        self.pdf_canvas.config(scrollregion=(0, 0, max_w, current_y))
        self.status_label.config(text=f"Loaded: {total_pages} Pages")
        self.progress.pack_forget() # Hide bar when done

    def _on_mousewheel(self, event):
        self.pdf_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def on_button_press(self, event):
        self.start_x, self.start_y = self.pdf_canvas.canvasx(event.x), self.pdf_canvas.canvasy(event.y)
        self.rect = self.pdf_canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2)

    def on_move_press(self, event):
        cur_x, cur_y = self.pdf_canvas.canvasx(event.x), self.pdf_canvas.canvasy(event.y)
        self.pdf_canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x, end_y = (self.pdf_canvas.canvasx(event.x), self.pdf_canvas.canvasy(event.y))
        self.pdf_canvas.delete(self.rect)
        self.process_snip(self.start_x, self.start_y, end_x, end_y)

    def process_snip(self, x1, y1, x2, y2):
        y_top = min(y1, y2)
        page_num = next((i for i, (s, e) in enumerate(self.page_offsets) if s <= y_top <= e), -1)
        if page_num == -1: return

        offset_y = self.page_offsets[page_num][0]
        page = self.doc.load_page(page_num)
        x_coords, y_coords = sorted([x1, x2]), sorted([y1 - offset_y, y2 - offset_y])
        
        clip = fitz.Rect(x_coords[0]/self.zoom, y_coords[0]/self.zoom, x_coords[1]/self.zoom, y_coords[1]/self.zoom)
        if clip.width < 5: return

        pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom), clip=clip)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.add_to_sidebar(img, page_num + 1)

    def add_to_sidebar(self, img, page_info):
        try: target_size = int(self.size_var.get())
        except: target_size = 600

        img.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
        card = Image.new("RGB", (target_size, target_size), "white")
        card.paste(img, ((target_size-img.size[0])//2, (target_size-img.size[1])//2))
        
        tk_img = ImageTk.PhotoImage(card)
        frame = tk.Frame(self.snip_list_frame, bd=1, relief="solid", bg="white")
        frame.pack(pady=10, padx=10)
        
        lbl = tk.Label(frame, image=tk_img, bg="white")
        lbl.image = tk_img
        lbl.pack()
        tk.Label(frame, text=f"Page {page_info}", bg="white", font=("Arial", 9, "bold")).pack()
        
        snip_entry = {"image": card, "page": page_info, "widget": frame}
        self.snippets_data.append(snip_entry)
        
        for w in [frame, lbl]: 
            w.bind("<Button-3>", lambda e: [frame.destroy(), self.snippets_data.remove(snip_entry)])

    def save_workspace(self):
        folder = filedialog.asksaveasfilename(title="Create Workspace Folder")
        if not folder: return
        if not os.path.exists(folder): os.makedirs(folder)
        manifest = {"pdf": self.pdf_path, "snippets": []}
        for i, snip in enumerate(self.snippets_data):
            name = f"snip_{i}.png"; snip["image"].save(os.path.join(folder, name))
            manifest["snippets"].append({"file": name, "page": snip["page"]})
        with open(os.path.join(folder, "workspace.json"), "w") as f: json.dump(manifest, f)
        messagebox.showinfo("Success", "Workspace Saved!")

    def load_workspace(self):
        folder = filedialog.askdirectory()
        if not folder or not os.path.exists(os.path.join(folder, "workspace.json")): return
        with open(os.path.join(folder, "workspace.json"), "r") as f: m = json.load(f)
        for s in self.snippets_data: s["widget"].destroy()
        self.snippets_data = []
        if os.path.exists(m["pdf"]): self.open_pdf(m["pdf"])
        for s in m["snippets"]:
            img = Image.open(os.path.join(folder, s["file"]))
            self.add_to_sidebar(img, s["page"])

if __name__ == "__main__":
    root = tk.Tk()
    app = SchematicSnipper(root)
    root.mainloop()