import tkinter as tk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import json
import os
import shutil

class SchematicSnipper:
    def __init__(self, root):
        self.root = root
        self.root.title("Schematic Troubleshooting Snipper (With Recall)")
        self.root.geometry("1400x900")
        
        # Variables
        self.doc = None
        self.pdf_path = ""
        self.current_page = 0
        self.zoom = 2.0
        self.target_snip_size = 300
        self.snippets_data = [] # Stores paths and metadata
        
        self.setup_ui()

    def setup_ui(self):
        # --- Toolbar ---
        toolbar = tk.Frame(self.root, bg="#2c3e50", pady=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        btn_style = {"bg": "#ecf0f1", "padx": 10}
        tk.Button(toolbar, text="📂 Open PDF", command=self.open_pdf, **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="💾 Save Workspace", command=self.save_workspace, bg="#27ae60", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="📂 Load Workspace", command=self.load_workspace, bg="#2980b9", fg="white").pack(side=tk.LEFT, padx=5)
        
        tk.Frame(toolbar, width=2, bg="gray").pack(side=tk.LEFT, fill=tk.Y, padx=10) # Divider
        
        tk.Button(toolbar, text="◀ Prev", command=lambda: self.change_page(-1)).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Next ▶", command=lambda: self.change_page(1)).pack(side=tk.LEFT, padx=2)
        
        self.page_label = tk.Label(toolbar, text="Page: 0/0", fg="white", bg="#2c3e50", font=("Arial", 10, "bold"))
        self.page_label.pack(side=tk.LEFT, padx=20)

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
        self.pdf_canvas = tk.Canvas(self.pdf_container, bg="#555", xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        self.pdf_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.v_scroll.config(command=self.pdf_canvas.yview)
        self.h_scroll.config(command=self.pdf_canvas.xview)

        # Snippet Sidebar
        self.snip_container = tk.Frame(self.paned, width=350, bg="#dcdde1")
        self.paned.add(self.snip_container, stretch="never")
        self.snip_canvas = tk.Canvas(self.snip_container, bg="#dcdde1", width=330)
        self.snip_scroll = tk.Scrollbar(self.snip_container, orient=tk.VERTICAL, command=self.snip_canvas.yview)
        self.snip_list_frame = tk.Frame(self.snip_canvas, bg="#dcdde1")
        self.snip_canvas.create_window((0, 0), window=self.snip_list_frame, anchor="nw")
        self.snip_canvas.configure(yscrollcommand=self.snip_scroll.set)
        self.snip_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.snip_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.snip_list_frame.bind("<Configure>", lambda e: self.snip_canvas.configure(scrollregion=self.snip_canvas.bbox("all")))

        self.pdf_canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.pdf_canvas.bind("<B1-Motion>", self.on_move_press)
        self.pdf_canvas.bind("<ButtonRelease-1>", self.on_button_release)

    # --- PDF & Snippet Logic ---
    def open_pdf(self, path=None):
        if not path:
            path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.pdf_path = path
            self.doc = fitz.open(path)
            self.current_page = 0
            self.render_page()

    def render_page(self):
        if not self.doc: return
        page = self.doc.load_page(self.current_page)
        pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.tk_img = ImageTk.PhotoImage(img)
        self.pdf_canvas.delete("all")
        self.pdf_canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        self.pdf_canvas.config(scrollregion=(0, 0, pix.width, pix.height))
        self.page_label.config(text=f"Page: {self.current_page + 1} / {len(self.doc)}")

    def change_page(self, delta):
        if self.doc:
            new_p = self.current_page + delta
            if 0 <= new_p < len(self.doc):
                self.current_page = new_p
                self.render_page()

    def on_button_press(self, event):
        self.start_x, self.start_y = self.pdf_canvas.canvasx(event.x), self.pdf_canvas.canvasy(event.y)
        self.rect = self.pdf_canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2)

    def on_move_press(self, event):
        cur_x, cur_y = self.pdf_canvas.canvasx(event.x), self.pdf_canvas.canvasy(event.y)
        self.pdf_canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x, end_y = self.pdf_canvas.canvasx(event.x), self.pdf_canvas.canvasy(event.y)
        self.create_snippet_widget(self.start_x, self.start_y, end_x, end_y)
        self.pdf_canvas.delete(self.rect)

    def create_snippet_widget(self, x1, y1, x2, y2, loaded_img=None, page_num=None):
        if not loaded_img:
            page = self.doc.load_page(self.current_page)
            x1, x2, y1, y2 = sorted([x1, x2]), sorted([x1, x2]), sorted([y1, y2]), sorted([y1, y2])
            clip = fitz.Rect(x1[0]/self.zoom, y1[0]/self.zoom, x2[1]/self.zoom, y2[1]/self.zoom)
            if clip.width < 10: return
            pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom), clip=clip)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            page_info = self.current_page + 1
        else:
            img = loaded_img
            page_info = page_num

        img.thumbnail((self.target_snip_size, self.target_snip_size))
        card = Image.new("RGB", (self.target_snip_size, self.target_snip_size), "white")
        card.paste(img, ((self.target_snip_size-img.size[0])//2, (self.target_snip_size-img.size[1])//2))
        
        tk_img = ImageTk.PhotoImage(card)
        frame = tk.Frame(self.snip_list_frame, bd=1, relief="solid", bg="white")
        frame.pack(pady=10, padx=10)
        lbl = tk.Label(frame, image=tk_img, bg="white")
        lbl.image = tk_img
        lbl.pack()
        tk.Label(frame, text=f"Page {page_info}", bg="white", font=("Arial", 8)).pack()
        
        # Store for saving
        snip_entry = {"image": card, "page": page_info, "widget": frame}
        self.snippets_data.append(snip_entry)
        
        def delete_snip(e):
            self.snippets_data.remove(snip_entry)
            frame.destroy()
        
        for w in [frame, lbl]: w.bind("<Button-3>", delete_snip)

    # --- Recall Features ---
    def save_workspace(self):
        if not self.snippets_data: return
        folder = filedialog.asksaveasfilename(title="Create Folder for Workspace")
        if not folder: return
        
        if not os.path.exists(folder): os.makedirs(folder)
        
        manifest = {"pdf": self.pdf_path, "snippets": []}
        for i, snip in enumerate(self.snippets_data):
            img_name = f"snip_{i}.png"
            snip["image"].save(os.path.join(folder, img_name))
            manifest["snippets"].append({"file": img_name, "page": snip["page"]})
            
        with open(os.path.join(folder, "workspace.json"), "w") as f:
            json.dump(manifest, f)
        messagebox.showinfo("Success", "Workspace Saved!")

    def load_workspace(self):
        folder = filedialog.askdirectory(title="Select Workspace Folder")
        if not folder: return
        
        json_path = os.path.join(folder, "workspace.json")
        if not os.path.exists(json_path):
            messagebox.showerror("Error", "Not a valid workspace folder.")
            return

        with open(json_path, "r") as f:
            manifest = json.load(f)

        # Clear current
        for s in self.snippets_data: s["widget"].destroy()
        self.snippets_data = []

        # Load PDF if possible
        if os.path.exists(manifest["pdf"]):
            self.open_pdf(manifest["pdf"])
        else:
            messagebox.showwarning("Warning", "Original PDF not found at original path. Please open it manually.")

        # Load snippets
        for s in manifest["snippets"]:
            img = Image.open(os.path.join(folder, s["file"]))
            self.create_snippet_widget(0,0,0,0, loaded_img=img, page_num=s["page"])

if __name__ == "__main__":
    root = tk.Tk()
    app = SchematicSnipper(root)
    root.mainloop()