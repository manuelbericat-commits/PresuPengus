import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from fpdf import FPDF
import os
import sys
import io
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw

# --- CORRECCIÓN DE RUTAS ---
if getattr(sys, 'frozen', False):
    CARPETA_ACTUAL = os.path.dirname(sys.executable)
else:
    CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))

# Rutas completas
ARCHIVO_CATALOGO = os.path.join(CARPETA_ACTUAL, 'catalogo.csv')
ARCHIVO_MATERIALES = os.path.join(CARPETA_ACTUAL, 'materiales.csv')
ARCHIVO_CONFIG = os.path.join(CARPETA_ACTUAL, 'config.csv')
ARCHIVO_LOGO = os.path.join(CARPETA_ACTUAL, 'logo.png')

COLOR_MARCA_HEX = "#fc9d03"
COLOR_RGB = (252, 157, 3) # Naranja
COLOR_TEXTO_RGB = (50, 50, 50) # Gris oscuro

# --- DATOS INICIALES ---
MATERIALES_DEFAULT = {
    "PLA Estándar": 15000, "PLA+ / Silk": 19000, "PETG": 17000,
    "ABS": 16000, "TPU (Flexible)": 28000, "Resina Estándar": 40000,
    "ASA": 22000, "Nylon": 45000, "PC (Policarbonato)": 35000,
    "HIPS": 18000, "PVA (Soluble)": 60000
}

# CAMBIO: Ahora guardamos valor_hora en lugar de mano_obra fija
CONFIG_DEFAULT = {"costo_minuto": 3.0, "valor_hora": 3000.0}

# --- CLASE PDF PERSONALIZADA ---
class PDFPro(FPDF):
    def footer(self):
        self.set_y(-20)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        txt = "El presupuesto tiene validez de 7 dias de corrido o hasta confirmar el pedido. DOCUMENTO NO VALIDO COMO FACTURA"
        self.cell(0, 10, txt, align='C')

class SistemaPresupuestos:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor Pengu 3D - Presupuestos Pro (Master)")
        self.root.geometry("1200x780")
        self.root.configure(bg="white")
        
        self.inicializar_db()
        self.df_prods = pd.read_csv(ARCHIVO_CATALOGO)
        self.df_mats = pd.read_csv(ARCHIVO_MATERIALES)
        self.df_conf = pd.read_csv(ARCHIVO_CONFIG)
        self.config_data = dict(zip(self.df_conf['clave'], self.df_conf['valor']))
        self.carrito = [] 

        style = ttk.Style()
        style.theme_use('clam')

        self.setup_header_logo()

        self.tabs = ttk.Notebook(root)
        self.tab_presu = tk.Frame(self.tabs, bg="white")
        self.tab_3d = tk.Frame(self.tabs, bg="white")
        self.tab_admin = tk.Frame(self.tabs, bg="white")
        
        self.tabs.add(self.tab_presu, text=" 1. Presupuesto ")
        self.tabs.add(self.tab_3d, text=" 2. Calculadora 3D ")
        self.tabs.add(self.tab_admin, text=" 3. Base de Datos (Admin) ")
        self.tabs.pack(expand=1, fill="both", padx=5, pady=5)

        self.setup_presupuesto()
        self.setup_calculadora_3d()
        self.setup_admin()

    def inicializar_db(self):
        if not os.path.exists(ARCHIVO_CATALOGO):
            pd.DataFrame({'nombre': ['Servicio Impresion'], 'precio': [500]}).to_csv(ARCHIVO_CATALOGO, index=False)
        if not os.path.exists(ARCHIVO_MATERIALES):
            df = pd.DataFrame(list(MATERIALES_DEFAULT.items()), columns=['material', 'precio_kg'])
            df.to_csv(ARCHIVO_MATERIALES, index=False)
        if not os.path.exists(ARCHIVO_CONFIG):
            df = pd.DataFrame(list(CONFIG_DEFAULT.items()), columns=['clave', 'valor'])
            df.to_csv(ARCHIVO_CONFIG, index=False)

    # --- HEADER ---
    def setup_header_logo(self):
        header_frame = tk.Frame(self.root, bg="white")
        header_frame.pack(fill="x", pady=(10, 0), padx=10)

        if os.path.exists(ARCHIVO_LOGO):
            try:
                pil_img = Image.open(ARCHIVO_LOGO)
                base_height = 70
                w_percent = (base_height / float(pil_img.size[1]))
                w_size = int((float(pil_img.size[0]) * float(w_percent)))
                pil_img = pil_img.resize((w_size, base_height), Image.Resampling.LANCZOS)
                self.logo_tk = ImageTk.PhotoImage(pil_img)
                lbl_logo = tk.Label(header_frame, image=self.logo_tk, bg="white")
                lbl_logo.pack(side="left")
                tk.Label(header_frame, text="  Pengu 3D", font=("Arial", 24, "bold"), bg="white", fg=COLOR_MARCA_HEX).pack(side="left", padx=(5,0))
                tk.Label(header_frame, text=" | Sistema de Gestión", font=("Arial", 16), bg="white", fg="gray").pack(side="left")
            except:
                 tk.Label(header_frame, text="[Error Logo]", bg="red", fg="white").pack(side="left")
        else:
            tk.Label(header_frame, text="Pengu 3D", font=("Arial", 24, "bold"), bg="white", fg=COLOR_MARCA_HEX).pack(side="left", padx=10)

    # --- PESTAÑA 1: PRESUPUESTO ---
    def setup_presupuesto(self):
        fr_top = tk.Frame(self.tab_presu, bg="white"); fr_top.pack(pady=10)
        tk.Label(fr_top, text="Cliente:", bg="white").grid(row=0, column=0)
        self.ent_cliente = tk.Entry(fr_top, width=25, bg="#f0f0f0"); self.ent_cliente.grid(row=0, column=1, padx=5)
        tk.Label(fr_top, text="Item:", bg="white").grid(row=0, column=2)
        self.combo_prod = ttk.Combobox(fr_top, values=self.df_prods['nombre'].tolist(), width=25); self.combo_prod.grid(row=0, column=3, padx=5)
        tk.Label(fr_top, text="Cant:", bg="white").grid(row=0, column=4)
        self.ent_cant = tk.Entry(fr_top, width=5, bg="#f0f0f0"); self.ent_cant.grid(row=0, column=5, padx=5)
        tk.Button(fr_top, text="+", command=self.agregar_manual, bg=COLOR_MARCA_HEX, fg="white", font=("Arial", 9, "bold"), width=3).grid(row=0, column=6, padx=5)
        self.tree = ttk.Treeview(self.tab_presu, columns=("c", "d", "u", "t"), show="headings", height=15)
        self.tree.heading("c", text="Cnt"); self.tree.column("c", width=40); self.tree.heading("d", text="Descripción"); self.tree.column("d", width=400)
        self.tree.heading("u", text="Unit"); self.tree.column("u", width=100); self.tree.heading("t", text="Total"); self.tree.column("t", width=100)
        self.tree.pack(pady=10, padx=20, fill="both", expand=True)
        fr_bot = tk.Frame(self.tab_presu, bg="white"); fr_bot.pack(fill="x", pady=20, padx=20)
        self.lbl_total = tk.Label(fr_bot, text="TOTAL: $ 0", font=("Arial", 20, "bold"), bg="white", fg=COLOR_MARCA_HEX); self.lbl_total.pack(side="right")
        tk.Button(fr_bot, text="GENERAR PDF", command=self.generar_pdf, bg="#27ae60", fg="white", font=("Arial", 12, "bold"), height=2).pack(side="left")

    # --- PESTAÑA 2: CALCULADORA 3D ---
    def setup_calculadora_3d(self):
        frame = tk.Frame(self.tab_3d, bg="white", padx=20, pady=20); frame.pack(expand=True)
        tk.Label(frame, text="CALCULADORA DE COSTOS", font=("Arial", 16, "bold"), fg=COLOR_MARCA_HEX, bg="white").grid(row=0, column=0, columnspan=2, pady=20)
        
        # Inputs
        tk.Label(frame, text="Material:", bg="white").grid(row=1, column=0, sticky="e"); self.combo_material = ttk.Combobox(frame, values=self.df_mats['material'].tolist(), state="readonly", width=27); self.combo_material.grid(row=1, column=1, pady=5); self.combo_material.bind("<<ComboboxSelected>>", self.actualizar_precio_rollo)
        tk.Label(frame, text="Costo Rollo (1kg): $", bg="white").grid(row=2, column=0, sticky="e"); self.c3d_costo_rollo = tk.Entry(frame, bg="#f9f9f9"); self.c3d_costo_rollo.grid(row=2, column=1, pady=5)
        tk.Label(frame, text="Peso (g):", bg="white").grid(row=3, column=0, sticky="e"); self.c3d_peso = tk.Entry(frame, bg="#f9f9f9"); self.c3d_peso.grid(row=3, column=1, pady=5)
        tk.Label(frame, text="Tiempo Impresión:", bg="white").grid(row=4, column=0, sticky="e"); fr_t = tk.Frame(frame, bg="white"); fr_t.grid(row=4, column=1, sticky="w"); self.c3d_h = tk.Entry(fr_t, width=5, bg="#e8f8f5"); self.c3d_h.pack(side="left"); tk.Label(fr_t, text="h ", bg="white").pack(side="left"); self.c3d_m = tk.Entry(fr_t, width=5, bg="#e8f8f5"); self.c3d_m.pack(side="left"); tk.Label(fr_t, text="m", bg="white").pack(side="left")
        
        # Configs cargadas
        tk.Label(frame, text="Costo Máquina ($/Min):", bg="white").grid(row=5, column=0, sticky="e"); self.c3d_costo_min = tk.Entry(frame, bg="#f9f9f9"); self.c3d_costo_min.insert(0, str(self.config_data.get('costo_minuto', 3.0))); self.c3d_costo_min.grid(row=5, column=1, pady=5)
        
        # --- CAMBIO AQUI: Horas de trabajo x Valor Hora ---
        lbl_mo = tk.Label(frame, text="Mano de Obra (Horas):", bg="white"); lbl_mo.grid(row=6, column=0, sticky="e")
        self.c3d_horas_mo = tk.Entry(frame, bg="#fff0c4") # Color amarillito para resaltar
        self.c3d_horas_mo.insert(0, "0")
        self.c3d_horas_mo.grid(row=6, column=1, pady=5)
        
        # Mostrar el valor hora actual como referencia
        self.valor_hora_actual = float(self.config_data.get('valor_hora', 3000.0))
        tk.Label(frame, text=f"(Valor actual: ${self.valor_hora_actual:.0f}/h)", font=("Arial", 8), fg="gray", bg="white").grid(row=6, column=2, sticky="w", padx=5)

        tk.Label(frame, text="Ganancia (%):", bg="white").grid(row=7, column=0, sticky="e"); self.c3d_margen = tk.Entry(frame, bg="#fff0c4"); self.c3d_margen.insert(0, "100"); self.c3d_margen.grid(row=7, column=1, pady=5)
        
        tk.Button(frame, text="CALCULAR", command=self.calcular_3d, bg="#3498db", fg="white", font=("Arial", 10, "bold"), width=30).grid(row=8, column=0, columnspan=2, pady=15)
        self.lbl_res_detalle = tk.Label(frame, text="", bg="white", fg="gray"); self.lbl_res_detalle.grid(row=9, column=0, columnspan=2)
        self.lbl_res_final = tk.Label(frame, text="PRECIO SUGERIDO: $ 0", font=("Arial", 16, "bold"), bg="white", fg=COLOR_MARCA_HEX); self.lbl_res_final.grid(row=10, column=0, columnspan=2, pady=10)
        tk.Button(frame, text="ENVIAR AL PRESUPUESTO ->", command=self.enviar_al_presupuesto, bg="#27ae60", fg="white", font=("Arial", 10)).grid(row=11, column=0, columnspan=2, pady=10, sticky="ew")

    def actualizar_precio_rollo(self, event):
        mat = self.combo_material.get()
        if mat in self.df_mats['material'].values:
            p = self.df_mats.loc[self.df_mats['material'] == mat, 'precio_kg'].values[0]
            self.c3d_costo_rollo.delete(0, 'end'); self.c3d_costo_rollo.insert(0, str(int(p)))

    def calcular_3d(self):
        try:
            peso = float(self.c3d_peso.get())
            hs = float(self.c3d_h.get() or 0); ms = float(self.c3d_m.get() or 0)
            rollo = float(self.c3d_costo_rollo.get()); c_min = float(self.c3d_costo_min.get())
            
            # --- CÁLCULO MANO DE OBRA ---
            horas_trabajo = float(self.c3d_horas_mo.get())
            valor_hora = float(self.config_data.get('valor_hora', 3000.0))
            costo_mo_total = horas_trabajo * valor_hora
            
            margen = float(self.c3d_margen.get())
            tot_min = (hs * 60) + ms
            
            c_mat = (rollo / 1000) * peso
            c_tiempo = c_min * tot_min
            
            base = c_mat + c_tiempo + costo_mo_total
            precio = base * (1 + (margen/100))
            
            self.lbl_res_detalle.config(text=f"Mat: ${c_mat:.0f} | Máq: ${c_tiempo:.0f} | MO: ${costo_mo_total:.0f} ({horas_trabajo}h) | Base: ${base:.0f}")
            self.lbl_res_final.config(text=f"PRECIO SUGERIDO: $ {precio:,.0f}")
            self.datos_3d = {'desc': f"Impresión 3D - {self.combo_material.get()} ({int(peso)}g)", 'precio': precio}
        except ValueError: messagebox.showerror("Error", "Revisa que todos los campos tengan números válidos.")

    def enviar_al_presupuesto(self):
        if hasattr(self, 'datos_3d'):
            d = self.datos_3d; self.carrito.append({'nom': d['desc'], 'cant': 1, 'pre': d['precio'], 'tot': d['precio']})
            self.tree.insert("", "end", values=(1, d['desc'], f"${d['precio']:,.0f}", f"${d['precio']:,.0f}")); self.actualizar_total(); self.tabs.select(0)
        else: messagebox.showwarning("!", "Calcula primero")

    # --- PESTAÑA 3: ADMIN ---
    def setup_admin(self):
        # 1. PRODUCTOS
        p_izq = tk.Frame(self.tab_admin, bg="white", padx=10, pady=10)
        p_izq.pack(side="left", fill="both", expand=True)
        tk.Label(p_izq, text="GESTIÓN PRODUCTOS", font=("Arial", 10, "bold"), fg="#2980b9", bg="white").pack(pady=5)
        tk.Label(p_izq, text="Seleccionar:", bg="white").pack()
        self.adm_prod_combo = ttk.Combobox(p_izq, values=self.df_prods['nombre'].tolist())
        self.adm_prod_combo.pack(); self.adm_prod_combo.bind("<<ComboboxSelected>>", self.cargar_producto_admin)
        tk.Label(p_izq, text="Nombre:", bg="white").pack(); self.adm_prod_n = tk.Entry(p_izq); self.adm_prod_n.pack()
        tk.Label(p_izq, text="Precio:", bg="white").pack(); self.adm_prod_p = tk.Entry(p_izq); self.adm_prod_p.pack()
        
        tk.Button(p_izq, text="Guardar Nuevo (+)", command=self.crear_producto, bg="#2ecc71", fg="white").pack(pady=5, fill='x')
        tk.Button(p_izq, text="Actualizar", command=self.modificar_producto, bg="#2980b9", fg="white").pack(pady=2, fill='x')
        tk.Button(p_izq, text="Eliminar (X)", command=self.eliminar_producto, bg="#e74c3c", fg="white").pack(pady=5, fill='x')
        tk.Button(p_izq, text="Limpiar", command=self.limpiar_admin_prod, bg="gray", fg="white").pack(pady=5)

        ttk.Separator(self.tab_admin, orient="vertical").pack(side="left", fill="y")

        # 2. MATERIALES
        p_cen = tk.Frame(self.tab_admin, bg="white", padx=10, pady=10)
        p_cen.pack(side="left", fill="both", expand=True)
        tk.Label(p_cen, text="GESTIÓN MATERIALES", font=("Arial", 10, "bold"), fg="#e67e22", bg="white").pack(pady=5)
        tk.Label(p_cen, text="Seleccionar:", bg="white").pack()
        self.adm_mat_combo = ttk.Combobox(p_cen, values=self.df_mats['material'].tolist())
        self.adm_mat_combo.pack(); self.adm_mat_combo.bind("<<ComboboxSelected>>", self.cargar_material_admin)
        tk.Label(p_cen, text="Nombre:", bg="white").pack(); self.adm_mat_n = tk.Entry(p_cen); self.adm_mat_n.pack()
        tk.Label(p_cen, text="Precio Kg:", bg="white").pack(); self.adm_mat_p = tk.Entry(p_cen); self.adm_mat_p.pack()
        
        tk.Button(p_cen, text="Guardar Nuevo (+)", command=self.crear_material, bg="#2ecc71", fg="white").pack(pady=5, fill='x')
        tk.Button(p_cen, text="Actualizar", command=self.modificar_material, bg="#e67e22", fg="white").pack(pady=2, fill='x')
        tk.Button(p_cen, text="Eliminar (X)", command=self.eliminar_material, bg="#e74c3c", fg="white").pack(pady=5, fill='x')
        tk.Button(p_cen, text="Limpiar", command=self.limpiar_admin_mat, bg="gray", fg="white").pack(pady=5)
        
        ttk.Separator(self.tab_admin, orient="vertical").pack(side="left", fill="y")

        # 3. CONFIGURACIÓN (ACTUALIZADA)
        p_der = tk.Frame(self.tab_admin, bg="white", padx=10, pady=10); p_der.pack(side="left", fill="both", expand=True)
        tk.Label(p_der, text="CONFIGURACIÓN GLOBAL", font=("Arial", 10, "bold"), fg="#27ae60", bg="white").pack(pady=5)
        
        tk.Label(p_der, text="Costo Máquina ($/min):", bg="white").pack()
        self.adm_conf_min = tk.Entry(p_der)
        self.adm_conf_min.insert(0, str(self.config_data.get('costo_minuto', 3.0)))
        self.adm_conf_min.pack()
        
        # CAMBIO: Configuración de Valor Hora
        tk.Label(p_der, text="Valor Hora Hombre ($):", bg="white").pack()
        self.adm_conf_hora = tk.Entry(p_der)
        self.adm_conf_hora.insert(0, str(self.config_data.get('valor_hora', 3000.0)))
        self.adm_conf_hora.pack()
        
        tk.Button(p_der, text="Guardar Configuración", command=self.guardar_config, bg="#27ae60", fg="white").pack(pady=10)

    # --- FUNCIONES ADMIN PRODUCTOS ---
    def cargar_producto_admin(self, event):
        nombre = self.adm_prod_combo.get()
        if nombre in self.df_prods['nombre'].values:
            precio = self.df_prods.loc[self.df_prods['nombre'] == nombre, 'precio'].values[0]
            self.adm_prod_n.delete(0, 'end'); self.adm_prod_n.insert(0, nombre)
            self.adm_prod_p.delete(0, 'end'); self.adm_prod_p.insert(0, str(int(precio)))
    def crear_producto(self):
        n, p = self.adm_prod_n.get(), self.adm_prod_p.get()
        if n and p:
            if n in self.df_prods['nombre'].values: messagebox.showwarning("!", "Ya existe."); return
            self.df_prods = pd.concat([self.df_prods, pd.DataFrame({'nombre': [n], 'precio': [float(p)]})], ignore_index=True)
            self.guardar_csv_prods(); messagebox.showinfo("OK", "Creado"); self.limpiar_admin_prod()
    def modificar_producto(self):
        orig, n, p = self.adm_prod_combo.get(), self.adm_prod_n.get(), self.adm_prod_p.get()
        if orig and n and p:
            idx = self.df_prods.index[self.df_prods['nombre'] == orig].tolist()
            if idx: self.df_prods.at[idx[0], 'nombre'] = n; self.df_prods.at[idx[0], 'precio'] = float(p); self.guardar_csv_prods(); messagebox.showinfo("OK", "Actualizado"); self.limpiar_admin_prod()
    def eliminar_producto(self):
        nombre = self.adm_prod_combo.get()
        if nombre and messagebox.askyesno("Confirmar", f"¿Eliminar '{nombre}'?"):
            self.df_prods = self.df_prods[self.df_prods['nombre'] != nombre]
            self.guardar_csv_prods(); messagebox.showinfo("Eliminado", "Borrado"); self.limpiar_admin_prod()
    def guardar_csv_prods(self):
        self.df_prods.to_csv(ARCHIVO_CATALOGO, index=False)
        lista = self.df_prods['nombre'].tolist()
        self.combo_prod['values'] = lista; self.adm_prod_combo['values'] = lista
    def limpiar_admin_prod(self):
        self.adm_prod_n.delete(0, 'end'); self.adm_prod_p.delete(0, 'end'); self.adm_prod_combo.set('')

    # --- FUNCIONES ADMIN MATERIALES ---
    def cargar_material_admin(self, event):
        mat = self.adm_mat_combo.get()
        if mat in self.df_mats['material'].values:
            p = self.df_mats.loc[self.df_mats['material'] == mat, 'precio_kg'].values[0]
            self.adm_mat_n.delete(0, 'end'); self.adm_mat_n.insert(0, mat)
            self.adm_mat_p.delete(0, 'end'); self.adm_mat_p.insert(0, str(int(p)))
    def crear_material(self):
        n, p = self.adm_mat_n.get(), self.adm_mat_p.get()
        if n and p:
            if n in self.df_mats['material'].values: messagebox.showwarning("!", "Ya existe."); return
            self.df_mats = pd.concat([self.df_mats, pd.DataFrame({'material': [n], 'precio_kg': [float(p)]})], ignore_index=True)
            self.guardar_csv_mats(); messagebox.showinfo("OK", "Creado"); self.limpiar_admin_mat()
    def modificar_material(self):
        orig, n, p = self.adm_mat_combo.get(), self.adm_mat_n.get(), self.adm_mat_p.get()
        if orig and n and p:
            idx = self.df_mats.index[self.df_mats['material'] == orig].tolist()
            if idx: self.df_mats.at[idx[0], 'material'] = n; self.df_mats.at[idx[0], 'precio_kg'] = float(p); self.guardar_csv_mats(); messagebox.showinfo("OK", "Actualizado"); self.limpiar_admin_mat()
    def eliminar_material(self):
        nombre = self.adm_mat_combo.get()
        if nombre and messagebox.askyesno("Confirmar", f"¿Eliminar '{nombre}'?"):
            self.df_mats = self.df_mats[self.df_mats['material'] != nombre]
            self.guardar_csv_mats(); messagebox.showinfo("Eliminado", "Borrado"); self.limpiar_admin_mat()
    def guardar_csv_mats(self):
        self.df_mats.to_csv(ARCHIVO_MATERIALES, index=False)
        lista = self.df_mats['material'].tolist()
        self.combo_material['values'] = lista; self.adm_mat_combo['values'] = lista
    def limpiar_admin_mat(self):
        self.adm_mat_n.delete(0, 'end'); self.adm_mat_p.delete(0, 'end'); self.adm_mat_combo.set('')

    # --- FUNCIONES GENERALES ---
    def guardar_config(self):
        try:
            # Guardamos 'valor_hora' en vez de 'mano_obra'
            val_min = float(self.adm_conf_min.get())
            val_hora = float(self.adm_conf_hora.get())
            df_new = pd.DataFrame({'clave': ['costo_minuto', 'valor_hora'], 'valor': [val_min, val_hora]})
            df_new.to_csv(ARCHIVO_CONFIG, index=False)
            self.config_data = dict(zip(df_new['clave'], df_new['valor']))
            messagebox.showinfo("Éxito", f"Configuración guardada.\nValor Hora: ${val_hora}")
        except: messagebox.showerror("Error", "Usa solo números")
    
    def agregar_manual(self):
        try:
            prod = self.combo_prod.get(); cant = int(self.ent_cant.get())
            if prod:
                prec = float(self.df_prods[self.df_prods['nombre']==prod]['precio'].values[0]); total = prec * cant
                self.carrito.append({'nom': prod, 'cant': cant, 'pre': prec, 'tot': total}); self.tree.insert("", "end", values=(cant, prod, f"${prec:,.0f}", f"${total:,.0f}")); self.actualizar_total(); self.ent_cant.delete(0, 'end')
        except: pass
    def actualizar_total(self): self.lbl_total.config(text=f"TOTAL: $ {sum(i['tot'] for i in self.carrito):,.0f}")

    def crear_barra_redondeada(self, width_mm, height_mm, color_rgb, radius_factor=1):
        scale = 12
        w_px, h_px = int(width_mm * scale), int(height_mm * scale)
        r_px = int(height_mm * scale * radius_factor)
        img = Image.new('RGBA', (w_px, h_px), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((0, 0, w_px, h_px), radius=r_px, fill=color_rgb)
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        return img_buffer

    def generar_pdf(self):
        if not self.carrito: return
        cliente = self.ent_cliente.get() or "Cliente"
        fecha_str = datetime.now().strftime('%d-%m-%Y')
        name_file = f"Presupuesto_{cliente}_{fecha_str}.pdf"
        pdf_path = os.path.join(CARPETA_ACTUAL, name_file)
        
        pdf = PDFPro()
        pdf.add_page()

        # 1. HEADER
        logo_width = 30; start_x = 10; start_y = 8
        if os.path.exists(ARCHIVO_LOGO):
            pdf.image(ARCHIVO_LOGO, start_x, start_y, logo_width)
            pdf.set_xy(start_x + logo_width + 5, start_y + 5)
            pdf.set_font("Arial", 'B', 24)
            pdf.set_text_color(0, 0, 0) # Negro
            pdf.cell(0, 10, "Pengu 3D", ln=True)
            
            pdf.set_xy(start_x + logo_width + 5, start_y + 15)
            pdf.set_font("Arial", 'B', 14)
            pdf.set_text_color(*COLOR_TEXTO_RGB)
            pdf.cell(0, 10, "PRESUPUESTO OFICIAL", ln=True)
        else:
            pdf.set_xy(start_x, 15)
            pdf.set_font("Arial", 'B', 24)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 10, "Pengu 3D - PRESUPUESTO", ln=True)

        # 2. SEPARADOR
        pdf.ln(5)
        barra_sep = self.crear_barra_redondeada(190, 3, COLOR_RGB, radius_factor=0.5)
        pdf.image(barra_sep, x=10, y=pdf.get_y(), w=190, h=3)
        pdf.ln(10)
        
        # 3. INFO
        pdf.set_text_color(*COLOR_TEXTO_RGB)
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 6, f"Cliente: {cliente}", ln=True)
        pdf.cell(0, 6, f"Fecha de emisión: {fecha_str}", ln=True)
        pdf.ln(8)

        # 4. TABLA
        header_bg = self.crear_barra_redondeada(190, 10, COLOR_RGB, radius_factor=0.3)
        current_y = pdf.get_y()
        pdf.image(header_bg, x=10, y=current_y, w=190, h=10)
        pdf.set_y(current_y)
        pdf.set_text_color(255); pdf.set_font("Arial", 'B', 10)
        pdf.cell(15, 10, "Cant", 0, 0, 'C'); pdf.cell(115, 10, "Descripción", 0, 0, 'L'); pdf.cell(30, 10, "Unitario", 0, 0, 'C'); pdf.cell(30, 10, "Total", 0, 1, 'C')
        
        pdf.set_text_color(*COLOR_TEXTO_RGB); pdf.set_font("Arial", '', 10)
        fill = False
        for i in self.carrito:
            pdf.cell(15, 9, str(i['cant']), 0, 0, 'C', fill)
            pdf.cell(115, 9, i['nom'], 0, 0, 'L', fill)
            pdf.cell(30, 9, f"${i['pre']:,.0f}", 0, 0, 'R', fill)
            pdf.cell(30, 9, f"${i['tot']:,.0f}", 0, 1, 'R', fill)
            pdf.set_fill_color(230, 230, 230)
            pdf.rect(10, pdf.get_y(), 190, 0.2, 'F')
            pdf.ln(1)

        # 5. TOTAL
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 16); pdf.set_text_color(*COLOR_RGB)
        pdf.cell(0, 10, f"TOTAL A PAGAR: $ {sum(c['tot'] for c in self.carrito):,.0f}", align='R')
        
        try: pdf.output(pdf_path); os.startfile(pdf_path)
        except: messagebox.showerror("Error", "Cierra el PDF abierto.")

if __name__ == "__main__":
    root = tk.Tk()
    app = SistemaPresupuestos(root)
    root.mainloop()