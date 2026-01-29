import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import json
import os

class SchematicSnipper:
    def __init__(self, root):
        self.root = root
        self.root.title("Schematic Snipper - Troubleshooting Pro")
        self.root.geometry("1600x950")
        
        # --- State ---
        self.zoom = 3.0  
        self.doc = None
        self.pdf_path = ""
        self.snippets_data = []
        self.page_images = []  
        self.page_offsets = [] 
        
        self.setup_ui()

    def setup_ui(self):
        # --- Toolbar ---
        self.toolbar = tk.Frame(self.root, bg="#2c3e50", pady=5)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        
        tk.Button(self.toolbar, text="📂 Open PDF", command=self.open_pdf, bg="#ecf0f1", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(self.toolbar, text="💾 Save Workspace", command=self.save_workspace, bg="#27ae60", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(self.toolbar, text="📂 Load Workspace", command=self.load_workspace, bg="#2980b9", fg="white").pack(side=tk.LEFT, padx=5)
        
        tk.Frame(self.toolbar, width=2, bg="gray").pack(side=tk.LEFT, fill=tk.Y, padx=10)

        tk.Label(self.toolbar, text="Quality:", fg="white", bg="#2c3e50").pack(side=tk.LEFT, padx=5)
        self.res_choice = ttk.Combobox(self.toolbar, values=["Standard (2x)", "High (3x)", "Ultra (4x)"], width=12)
        self.res_choice.current(1) 
        self.res_choice.pack(side=tk.LEFT, padx=5)
        self.res_choice.bind("<<ComboboxSelected>>", self.update_resolution)

        tk.Label(self.toolbar, text="Snip Width:", fg="white", bg="#2c3e50").pack(side=tk.LEFT, padx=10)
        self.size_var = tk.StringVar(value="400") 
        tk.Entry(self.toolbar, textvariable=self.size_var, width=5).pack(side=tk.LEFT)
        
        self.progress = ttk.Progressbar(self.toolbar, orient=tk.HORIZONTAL, length=150, mode='determinate')
        self.progress.pack(side=tk.RIGHT, padx=10)
        self.progress.pack_forget() 
        self.status_label = tk.Label(self.toolbar, text="Ready", fg="white", bg="#2c3e50")
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # --- Main Layout ---
        self.paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=6, bg="#444")
        self.paned.pack(fill=tk.BOTH, expand=True)

        # Left Side: PDF Viewer
        self.pdf_container = tk.Frame(self.paned)
        self.paned.add(self.pdf_container, stretch="always")
        self.v_scroll = tk.Scrollbar(self.pdf_container); self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scroll = tk.Scrollbar(self.pdf_container, orient=tk.HORIZONTAL); self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.pdf_canvas = tk.Canvas(self.pdf_container, bg="#1e1e1e", xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        self.pdf_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.v_scroll.config(command=self.pdf_canvas.yview); self.h_scroll.config(command=self.pdf_canvas.xview)

        # Right Side: Snippet Grid (2 Columns)
        self.snip_container = tk.Frame(self.paned, width=850, bg="#dcdde1")
        self.paned.add(self.snip_container, stretch="never")
        self.snip_canvas = tk.Canvas(self.snip_container, bg="#dcdde1")
        self.snip_scroll = tk.Scrollbar(self.snip_container, orient=tk.VERTICAL, command=self.snip_canvas.yview)
        self.snip_list_frame = tk.Frame(self.snip_canvas, bg="#dcdde1")
        self.snip_canvas.create_window((0, 0), window=self.snip_list_frame, anchor="nw")
        self.snip_canvas.configure(yscrollcommand=self.snip_scroll.set)
        self.snip_scroll.pack(side=tk.RIGHT, fill=tk.Y); self.snip_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.snip_list_frame.bind("<Configure>", lambda e: self.snip_canvas.configure(scrollregion=self.snip_canvas.bbox("all")))

        self.pdf_canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.pdf_canvas.bind("<B1-Motion>", self.on_move_press)
        self.pdf_canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.pdf_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def update_resolution(self, event=None):
        val = self.res_choice.get()
        if "Standard" in val: self.zoom = 2.0
        elif "High" in val: self.zoom = 3.0
        elif "Ultra" in val: self.zoom = 4.0
        if self.doc:
            if messagebox.askyesno("Re-render", "Reload PDF at new quality?"):
                self.render_all_pages()

    def open_pdf(self, path=None):
        if not path:
            path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.pdf_path = path
            self.doc = fitz.open(path)
            self.render_all_pages()

    def render_all_pages(self):
        self.pdf_canvas.delete("all")
        self.page_images, self.page_offsets = [], []
        current_y, max_w = 0, 0
        self.progress.pack(side=tk.RIGHT, padx=10); self.progress['maximum'] = len(self.doc)
        
        for i, page in enumerate(self.doc):
            self.status_label.config(text=f"Rendering PDF... Page {i+1}/{len(self.doc)}")
            pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom), colorspace=fitz.csRGB)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            tk_img = ImageTk.PhotoImage(img)
            self.page_offsets.append((current_y, current_y + pix.height))
            self.pdf_canvas.create_image(0, current_y, anchor=tk.NW, image=tk_img)
            self.page_images.append(tk_img)
            current_y += pix.height + 30
            max_w = max(max_w, pix.width)
            self.progress['value'] = i + 1
            self.root.update_idletasks()
        
        self.pdf_canvas.config(scrollregion=(0, 0, max_w, current_y))
        self.status_label.config(text=f"Done - {len(self.doc)} Pages")
        self.progress.pack_forget()

    def on_button_press(self, event):
        self.start_x, self.start_y = self.pdf_canvas.canvasx(event.x), self.pdf_canvas.canvasy(event.y)
        self.rect = self.pdf_canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='cyan', width=2)

    def on_move_press(self, event):
        cur_x, cur_y = self.pdf_canvas.canvasx(event.x), self.pdf_canvas.canvasy(event.y)
        self.pdf_canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x, end_y = self.pdf_canvas.canvasx(event.x), self.pdf_canvas.canvasy(event.y)
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

    def add_to_sidebar(self, img, page_info, initial_note=""):
        try: target_w = int(self.size_var.get())
        except: target_w = 400
        
        ratio = target_w / float(img.size[0])
        target_h = int(float(img.size[1]) * float(ratio))
        img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(img)
        
        frame = tk.Frame(self.snip_list_frame, bd=1, relief="solid", bg="black")
        lbl = tk.Label(frame, image=tk_img, bg="white")
        lbl.image = tk_img 
        lbl.pack()
        
        # Metadata Label
        tk.Label(frame, text=f"SHEET: {page_info}", bg="#2c3e50", fg="white", font=("Verdana", 8, "bold")).pack(fill=tk.X)
        
        # Interactive Note Entry
        note_entry = tk.Entry(frame, bg="#34495e", fg="white", insertbackground="white", font=("Arial", 9), relief="flat")
        if initial_note:
            note_entry.insert(0, initial_note)
        else:
            note_entry.insert(0, "Click to add note...")
        note_entry.pack(fill=tk.X, padx=2, pady=2)

        def clear_placeholder(e):
            if note_entry.get() == "Click to add note...":
                note_entry.delete(0, tk.END)

        note_entry.bind("<FocusIn>", clear_placeholder)
        
        snip_entry = {"image": img, "page": page_info, "widget": frame, "note_widget": note_entry}
        self.snippets_data.append(snip_entry)
        self.reorder_grid()

        lbl.bind("<Button-3>", lambda e: [frame.destroy(), self.snippets_data.remove(snip_entry), self.reorder_grid()])

    def reorder_grid(self):
        for i, snip in enumerate(self.snippets_data):
            row, col = i // 2, i % 2
            snip["widget"].grid(row=row, column=col, padx=5, pady=5, sticky="n")

    def _on_mousewheel(self, event):
        self.pdf_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def save_workspace(self):
        folder = filedialog.askdirectory(title="Save Workspace Folder")
        if not folder: return
        manifest = {"pdf": self.pdf_path, "snippets": []}
        for i, snip in enumerate(self.snippets_data):
            name = f"snip_{i}.png"
            snip["image"].save(os.path.join(folder, name))
            note_val = snip["note_widget"].get()
            if note_val == "Click to add note...": note_val = ""
            manifest["snippets"].append({"file": name, "page": snip["page"], "note": note_val})
        
        with open(os.path.join(folder, "workspace.json"), "w") as f:
            json.dump(manifest, f)
        messagebox.showinfo("Saved", "Workspace & Notes Saved.")

    def load_workspace(self):
        folder = filedialog.askdirectory(title="Select Workspace Folder")
        if not folder or not os.path.exists(os.path.join(folder, "workspace.json")): return
        with open(os.path.join(folder, "workspace.json"), "r") as f:
            m = json.load(f)
        
        for s in self.snippets_data: s["widget"].destroy()
        self.snippets_data = []

        if os.path.exists(m["pdf"]):
            self.open_pdf(m["pdf"])
        
        for s in m["snippets"]:
            img_path = os.path.join(folder, s["file"])
            if os.path.exists(img_path):
                img = Image.open(img_path)
                self.add_to_sidebar(img, s["page"], initial_note=s.get("note", ""))

if __name__ == "__main__":
    root = tk.Tk()
    app = SchematicSnipper(root)
    root.mainloop()