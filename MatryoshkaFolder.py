import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from send2trash import send2trash

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def get_directory_tree(path):
    """Escanea recursivamente y devuelve la estructura de árbol completa con tamaños."""
    try:
        entries_list = []
        total_size = 0
        with os.scandir(path) as entries:
            for entry in entries:
                is_dir = entry.is_dir(follow_symlinks=False)
                item_size = 0
                children = []
                
                if is_dir:
                    try:
                        item_size, children = get_directory_tree(entry.path)
                    except PermissionError:
                        item_size = 0
                else:
                    try:
                        item_size = entry.stat(follow_symlinks=False).st_size
                    except (PermissionError, FileNotFoundError):
                        item_size = 0
                
                total_size += item_size
                entries_list.append({
                    'name': entry.name,
                    'path': entry.path,
                    'size': item_size,
                    'is_dir': is_dir,
                    'children': children
                })
        entries_list.sort(key=lambda x: x['size'], reverse=True)
        return total_size, entries_list
    except PermissionError:
        return 0, []

class MatryoshkaApp(ctk.CTk):
    def __init__(self, target_path):
        super().__init__()
        
        self.current_path = os.path.abspath(target_path)
        self.history = []
        self.item_paths = {}
        
        self.title("MatryoshkaFolder")
        self.geometry("1050x560")
        self.minsize(800, 400)
        
        # --- Cabecera ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(15, 10))
        
        self.left_header = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.left_header.pack(side="left", fill="y")
        
        self.lbl_title = ctk.CTkLabel(
            self.left_header, 
            text="📂 MatryoshkaFolder", 
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
        )
        self.lbl_title.pack(side="left", padx=(0, 10))
        
        self.btn_back = ctk.CTkButton(
            self.left_header, 
            text="⬅ Volver", 
            width=80, 
            height=28,
            command=self.go_back,
            fg_color="#333333",
            hover_color="#444444"
        )
        self.btn_back.pack_forget()
        
        self.lbl_path = ctk.CTkLabel(
            self.header_frame, 
            text="", 
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="gray"
        )
        self.lbl_path.pack(side="right", padx=5)
        
        # --- Contenedor de la Tabla ---
        self.table_frame = ctk.CTkFrame(self, fg_color=("gray90", "gray16"))
        self.table_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        style = ttk.Style()
        style.theme_use("clam")
        
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg_color = "#1f1f1f" if is_dark else "#f0f0f0"
        text_color = "#ffffff" if is_dark else "#000000"
        select_bg = "#1f538d" if is_dark else "#3a7ebf"
        
        style.configure(
            "Treeview",
            background=bg_color,
            foreground=text_color,
            fieldbackground=bg_color,
            borderwidth=0,
            rowheight=28,
            font=("Segoe UI", 10)
        )
        style.configure(
            "Treeview.Heading",
            background="#2b2b2b" if is_dark else "#e1e1e1",
            foreground=text_color,
            font=("Segoe UI", 10, "bold"),
            borderwidth=0
        )
        style.map("Treeview", background=[('selected', select_bg)], foreground=[('selected', '#ffffff')])
        
        columns = ("tipo", "tamano", "porcentaje", "barra")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, selectmode="browse")
        
        self.tree.heading("#0", text="Nombre")
        self.tree.heading("tipo", text="Tipo")
        self.tree.heading("tamano", text="Tamaño")
        self.tree.heading("porcentaje", text="%")
        self.tree.heading("barra", text="Distribución Visual")
        
        self.tree.column("#0", width=280, minwidth=200, anchor="w")
        self.tree.column("tipo", width=90, anchor="center")
        self.tree.column("tamano", width=100, anchor="e")
        self.tree.column("porcentaje", width=80, anchor="e")
        self.tree.column("barra", width=260, anchor="e")
        
        # Eventos: Doble clic para navegar / Clic derecho para menú contextual
        self.tree.bind("<Double-1>", self.on_item_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        # Menú contextual de Clic Derecho
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="🗑️️ Enviar a la papelera", command=self.delete_selected_item)
        
        self.scrollbar = ctk.CTkScrollbar(self.table_frame, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)
        self.scrollbar.pack(side="right", fill="y", padx=5, pady=5)
        
        # --- Barra inferior ---
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.pack(fill="x", padx=20, pady=(5, 15))
        
        self.lbl_status = ctk.CTkLabel(
            self.footer_frame, 
            text="", 
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray"
        )
        self.lbl_status.pack(side="left")
        
        self.load_path(self.current_path)

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    def load_path(self, path):
        self.current_path = path
        self.lbl_path.configure(text=f"Analizando: {self.current_path}")
        self.lbl_status.configure(text="Escaneando estructura de carpetas...")
        self.tree.delete(*self.tree.get_children())
        self.item_paths.clear()
        
        if self.history:
            self.btn_back.pack(side="left", padx=(0, 10))
        else:
            self.btn_back.pack_forget()
            
        threading.Thread(target=self.scan_thread, args=(path,), daemon=True).start()

    def scan_thread(self, path):
        total_size, items = get_directory_tree(path)
        self.after(0, lambda: self.populate_tree("", items, total_size, max_bar_len=16))
        self.lbl_status.configure(text=f"Escaneo completo. 100% actual: {self.format_size(total_size)}")

    def populate_tree(self, parent_id, items, parent_size, max_bar_len):
        for item in items:
            percentage = (item['size'] / parent_size) * 100 if parent_size > 0 else 0
            tipo = "Carpeta" if item['is_dir'] else "Archivo"
            icon = "📁 " if item['is_dir'] else "📄 "
            tamano_str = self.format_size(item['size'])
            porcentaje_str = f"{percentage:.2f}%"
            
            display_name = item['name']
            if len(display_name) > 32:
                display_name = display_name[:29] + "..."

            current_bar_len = max(4, int(max_bar_len * 0.90))
            filled_length = int(current_bar_len * percentage // 100)
            visual_bar = "█" * filled_length + "░" * (current_bar_len - filled_length)

            node_id = self.tree.insert(
                parent_id, 
                "end", 
                text=icon + display_name, 
                values=(tipo, tamano_str, porcentaje_str, visual_bar)
            )
            
            self.item_paths[node_id] = {'path': item['path'], 'is_dir': item['is_dir'], 'name': item['name']}
            
            if item['is_dir'] and item['children']:
                self.populate_tree(node_id, item['children'], item['size'], current_bar_len)

    def on_item_double_click(self, event):
        selected_item = self.tree.focus()
        if not selected_item:
            return
            
        item_data = self.item_paths.get(selected_item)
        if item_data and item_data['is_dir']:
            self.history.append(self.current_path)
            self.load_path(item_data['path'])

    def show_context_menu(self, event):
        # Seleccionar la fila sobre la que se hizo clic derecho
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
            self.tree.focus(item_id)
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def delete_selected_item(self):
        selected_item = self.tree.focus()
        if not selected_item:
            return
            
        item_data = self.item_paths.get(selected_item)
        if not item_data:
            return
            
        path_to_delete = item_data['path']
        name = item_data['name']
        
        # Cuadro de confirmación nativo antes de tirar a la papelera
        confirm = messagebox.askyesno(
            "Enviar a la papelera", 
            f"¿Estás seguro de que querés enviar '{name}' a la papelera de reciclaje?"
        )
        
        if confirm:
            try:
                send2trash(path_to_delete)
                # Recargar la vista actual para reflejar el espacio liberado y el archivo borrado
                self.load_path(self.current_path)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar el archivo:\n{e}")

    def go_back(self):
        if self.history:
            prev_path = self.history.pop()
            self.load_path(prev_path)

if __name__ == "__main__":
    path_to_sys = sys.argv[1] if len(sys.argv) > 1 else "."
    app = MatryoshkaApp(path_to_sys)
    app.mainloop()