import tkinter as tk
from tkinter import messagebox
import pandas as pd
import numpy as np
import customtkinter as ctk
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
import firebase_admin
from firebase_admin import credentials, db
import threading
import os
import atexit

logging.basicConfig(level=logging.INFO)
handler = RotatingFileHandler("app.log", maxBytes=1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)

try:
    cred = credentials.Certificate("firebasekey.json")
    firebase_admin.initialize_app(cred, {'databaseURL': 'https://your_url_here.firebaseio.com/'})
except ValueError:
    pass 

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

Pilotos = ["Arturo", "Jorge", "Fredy", "Renato", "Andrea", "Sebastian", "Diana", "Miguel", "Jesus", "Luis", "Felipe", "Roberto", "Alexis"]

Sitio_Dict = {
    "New_York": ["Giraffe", "Elephant", "Dog", "Cat", "Wolf"],
    "Tokyo": ["Katakana", "Hiragana"],
    "Honk_Kong": ["T1", "T2", "T3", "T4", "T5", "T6", "T7"],
    "Seul": ["SLC1", "SLC2"]
}

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ArcBest Register")
        self.geometry(f"{1000}x{420}")
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=1)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.resizable(False, False)
        atexit.register(self.on_close)

        #Variables
        self.usuario_seleccionado = None
        self.site_seleccionado = None
        self.log_completo = "Esperando Actividad..."
        self.pilotos_widgets = {}
        self.botones_vehiculos = {}

        #Seccion 1
        self.sidebar_frame = ctk.CTkFrame(self, width=100, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=5, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.label_tiempo = ctk.CTkLabel(self.sidebar_frame, text="00:00:00", font=ctk.CTkFont(size=20, weight="bold"))
        self.label_tiempo.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.label_tiempo.pack(pady=10)

        self.btn_login = ctk.CTkButton(self.sidebar_frame, text="Cambiar Sesión", command=self.cambiar_sesion)
        self.btn_login.pack(pady=20)
        self.login_window = None

        self.btn_turno = ctk.CTkButton(self.sidebar_frame, text="Iniciar Turno", command=self.gestionar_turno)
        self.btn_turno.pack(pady=10)

        self.usuarios_frame = ctk.CTkScrollableFrame(self.sidebar_frame, label_text="Usuarios", width=150, height=200)
        self.usuarios_frame.pack(pady=10, fill="both", expand=True)

        self.inicio_turno = None
        self.cronometro_activo = False
        self.pallet_count = 0

        #Seccion 2 A
        self.frame_palete = ctk.CTkFrame(self, width=200, fg_color="transparent")
        self.frame_palete.grid(row=0, column=1, rowspan=5, sticky="nsew")
        self.frame_palete.grid_columnconfigure(0, weight=1)
        self.frame_palete.grid_columnconfigure(1, weight=1)
        self.frame_palete.grid_rowconfigure(2, weight=1)

        self.pallet_label = ctk.CTkLabel(self.frame_palete, text="Palletes", font=ctk.CTkFont(size=16, weight="bold"))
        self.pallet_label.grid(row=0, column=0, columnspan=2, padx=(20), pady=(0, 5), sticky="ew")
 
        self.pallet_add = ctk.CTkButton(self.frame_palete, text="Agregar Pallete", command=lambda: self.actualizar_palletes(int(1)))
        self.pallet_add.grid(row=1, column=0, padx=(20, 10), pady=(10), sticky="nsew")
        self.pallet_remove = ctk.CTkButton(self.frame_palete, text="Eliminar Pallete", command=lambda: self.actualizar_palletes(int(-1)))
        self.pallet_remove.grid(row=1, column=1, padx=(10, 20), pady=(10), sticky="nsew")

        self.section_3_frame = ctk.CTkFrame(self, width=200, height=100, fg_color="transparent")
        self.section_3_frame.grid(row=1, column=2, sticky="nsew")
        self.section_3_frame.grid_rowconfigure(5, weight=1)

        #Seccion 2 B
        self.frame_palete = ctk.CTkFrame(self, width=200, fg_color="transparent")
        self.frame_palete.grid(row=0, column=2, rowspan=5, sticky="nsew")

        self.log_label = ctk.CTkLabel(self.frame_palete, text=self.log_completo, font=ctk.CTkFont(size=10), justify="left")
        self.log_label.grid(row=2, column=0, columnspan=2, padx=(20), pady=(10, 5), sticky="ew")

        self.frame_vehiculos = ctk.CTkFrame(self, width=200, height=100, fg_color="transparent")
        self.frame_vehiculos.grid(row=2, column=1, sticky="nsew")

    def iniciar_listener(self):
        def callback(event):
            usuarios = db.reference("/usuarios/").get()
            if self.winfo_exists() and usuarios:
                self.after(0, lambda: self.mostrar_pilotos_activos(usuarios))
        db.reference('usuarios').listen(callback)

    def mostrar_vehiculos(self):
        for widget in self.frame_vehiculos.winfo_children():
            widget.destroy()
        self.botones_vehiculos = {}

        sitio_actual = self.Site.get()
        vehiculos = Sitio_Dict.get(sitio_actual, [])

        for n in range(4):
            self.frame_vehiculos.grid_columnconfigure(n, weight=1)

        for i, nombre_vehiculo in enumerate(vehiculos):
            fila = i // 4
            columna = i % 4
            
            btn = ctk.CTkButton(self.frame_vehiculos, text=nombre_vehiculo)
            btn.configure(command=lambda b=btn, v=nombre_vehiculo: self.seleccionar_vehiculo(v, b))
            btn.grid(row=fila, column=columna, padx=5, pady=5, sticky="nsew")
            self.botones_vehiculos[nombre_vehiculo] = btn
        self.iniciar_listener_vehiculos(sitio_actual)

    def iniciar_listener_vehiculos(self, sitio):
        def callback(event):
            datos_sitio = db.reference(f'sitios/{sitio}').get()
            if datos_sitio:
                self.after(0, lambda: self.actualizar_colores_tiempo_real(datos_sitio))
        db.reference(f'sitios/{sitio}').listen(callback)

    def actualizar_colores_tiempo_real(self, datos):
        COLOR_OCUPADO = "#7B3030"
        COLOR_MIO = "#2fa572"
        COLOR_NORMAL = "#3a3a3a"

        for nombre_v, info in datos.items():
            if nombre_v in self.botones_vehiculos:
                btn = self.botones_vehiculos[nombre_v]
                status = info.get("status", "offline")
                usuario_que_lo_tiene = info.get("user", "none")

                if status == "online" and usuario_que_lo_tiene != self.usuario_seleccionado:
                    btn.configure(
                        fg_color=COLOR_OCUPADO, 
                        state="disabled",
                        text=f"{nombre_v}\n({usuario_que_lo_tiene})"
                    )

                elif status == "online" and usuario_que_lo_tiene == self.usuario_seleccionado:
                    btn.configure(
                        fg_color=COLOR_MIO, 
                        state="normal", 
                        text=f"{nombre_v}\n(Tú)"
                    )

                else:
                    btn.configure(
                        fg_color=COLOR_NORMAL, 
                        state="normal", 
                        text=nombre_v
                    )

    def mostrar_pilotos_activos(self, datos_firebase):
        VERDE_CTK = "#2fa572"
        GRIS_HUECO = "#666666"

        if not hasattr(self, 'pilotos_widgets'):
            self.pilotos_widgets = {}

        pilotos_ordenados = sorted(datos_firebase.items(), key=lambda item: (0 if item[1].get("estado") == "online" else 1, item[0]))

        for nombre, info in pilotos_ordenados:
            estado = info.get("estado", "offline")
            simbolo = "●" if estado == "online" else "○"
            color = VERDE_CTK if estado == "online" else GRIS_HUECO
            texto_completo = f"{simbolo} {nombre}"

            if nombre in self.pilotos_widgets:
                lbl = self.pilotos_widgets[nombre]
                lbl.configure(text=texto_completo, text_color=color)
                lbl.pack_forget()
                lbl.pack(fill="x", padx=10, pady=2)
            else:
                lbl = ctk.CTkLabel(
                    self.usuarios_frame, 
                    text=texto_completo, 
                    text_color=color,
                    anchor="w",
                    font=ctk.CTkFont(size=12, weight="bold")
                )
                lbl.pack(fill="x", padx=10, pady=2)
                self.pilotos_widgets[nombre] = lbl

    def seleccionar_vehiculo(self, nombre_v, boton):
        sitio = self.Site.get()
        ref = db.reference(f'sitios/{sitio}/{nombre_v}')
        actual = ref.get()
        ahora = time.strftime("%H:%M:%S")
        if actual.get("status") == "offline":
            ref.update({
                "status": "online",
                "user": self.usuario_seleccionado
            })
            self.agregar_log(f"Seleccionaste {nombre_v} en {sitio} a las {ahora}")
        else:
            ref.update({
                "status": "offline",
                "user": "none"
            })
            self.agregar_log(f"Dejaste {nombre_v} en {sitio} a las {ahora}")


    def agregar_log(self, mensaje):
        self.log_completo += f"\n> {mensaje}"
        self.log_label.configure(text=self.log_completo)

    def actualizar_palletes(self, count):
        self.pallet_count = self.pallet_count + count
        self.pallet_label.configure(text=f"Palletes: {self.pallet_count}")
        ahora = time.strftime("%H:%M:%S")
        self.agregar_log(f"{'Agregado' if count > 0 else 'Eliminado'} un pallete a las {ahora}. Total: {self.pallet_count}")

    def login(self):
        if self.login_window is None or not self.login_window.winfo_exists():
            self.login_window = ctk.CTkToplevel(self)
            self.login_window.title("Login")
            self.login_window.geometry("300x300")
            self.login_window.after(10, self.login_window.lift)
            self.login_window.attributes("-topmost", True)
            self.login_window.protocol("WM_DELETE_WINDOW", lambda: None)

            self.login_window.wait_visibility()
            self.login_window.grab_set()
            self.login_window.transient(self)

            label = ctk.CTkLabel(self.login_window, text="¡Bienvenido Arcbestiano!", font=("Arial", 20))
            label.pack(pady=20)

            self.Usuario = ctk.CTkOptionMenu(self.login_window, values=Pilotos)
            self.Usuario.set("Piloto")
            self.Usuario.pack(pady=10)
            self.Site = ctk.CTkOptionMenu(self.login_window, values=list(Sitio_Dict.keys()))
            self.Site.set("Sitio")
            self.Site.pack(pady=10)

            btn_cerrar = ctk.CTkButton(self.login_window, text="Aceptar", command=self.finalizar_login)
            btn_cerrar.pack(pady=10)
            self.wait_window(self.login_window)

    def cambiar_sesion(self):
        respuesta = messagebox.askokcancel(title="Cambiar Sesión", message="¿Estás seguro de que deseas cambiar de sesión? Esto reiniciará el cronómetro y el conteo de palletes.", parent=self, icon="warning")
        if respuesta:
            self.agregar_log(f"Sesión de {self.usuario_seleccionado} en {self.site_seleccionado} cerrada a las {time.strftime('%H:%M:%S')}")
            self.cambiar_estatus_firebase("offline")
            self.usuario_seleccionado = None
            self.site_seleccionado = None
            self.cronometro_activo = False
            self.pallet_count = 0
            self.label_tiempo.configure(text="00:00:00")
            self.pallet_label.configure(text="Palletes: 0")
            self.btn_turno.configure(text="Iniciar Turno", fg_color="green")
            self.login()

    def finalizar_login(self):
        self.usuario_seleccionado = self.Usuario.get()
        self.site_seleccionado = self.Site.get()

        if self.usuario_seleccionado == "Piloto" or self.site_seleccionado == "Sitio":
            messagebox.showerror("Error", "Por favor, seleccione un piloto y un sitio válidos.", parent=self.login_window, icon="error")
        else:
            self.agregar_log(f"Iniciando sesión como {self.usuario_seleccionado} en {self.site_seleccionado} a las {time.strftime('%H:%M:%S')}")
            self.mostrar_vehiculos()
            self.cambiar_estatus_firebase("online")
            threading.Thread(target=self.iniciar_listener, daemon=True).start()
            self.login_window.destroy()

    def cambiar_estatus_firebase(self, nuevo_estado):
        if hasattr(self, 'usuario_seleccionado'):
            ref = db.reference(f'usuarios/{self.usuario_seleccionado}')
            ref.update({"estado": nuevo_estado, "ultima_conexion": time.strftime("%H:%M:%S")})
            if nuevo_estado == "offline":
                sitio = self.Site.get()
                ref_sitio = db.reference(f'sitios/{sitio}')
                vehiculos_data = ref_sitio.get()

                if vehiculos_data:
                    for nombre_v, info in vehiculos_data.items():
                        if info.get("status") == "online" and info.get("user") == self.usuario_seleccionado:
                            ref_especifica = db.reference(f'sitios/{sitio}/{nombre_v}')
                            ref_especifica.update({
                                "status": "offline",
                                "user": "none"
                            })

    def gestionar_turno(self):
        if not self.cronometro_activo:
            self.agregar_log(f"Turno iniciado por {self.usuario_seleccionado} en {self.site_seleccionado} a las {time.strftime('%H:%M:%S')}")
            self.inicio_turno = time.time()
            self.cronometro_activo = True
            self.btn_turno.configure(text="Finalizar Turno", fg_color="red")
            self.actualizar_cronometro()
        else:
            self.agregar_log(f"Turno terminado por {self.usuario_seleccionado} en {self.site_seleccionado} a las {time.strftime('%H:%M:%S')}")
            self.cronometro_activo = False
            self.btn_turno.configure(text="Iniciar Turno", fg_color="green")

    def actualizar_cronometro(self):
        if self.cronometro_activo:
            tiempo_actual = time.time() - self.inicio_turno
            horas = int(tiempo_actual // 3600)
            minutos = int((tiempo_actual % 3600) // 60)
            segundos = int(tiempo_actual % 60)
            self.label_tiempo.configure(text=f"{horas:02d}:{minutos:02d}:{segundos:02d}")
            self.after(1000, self.actualizar_cronometro)
    
    def on_close(self):
        self.agregar_log(f"Guardando log a las {time.strftime('%H:%M:%S')}...")
        self.cambiar_estatus_firebase("offline")
        self.quit()
        self.destroy()
        sys.exit()

app = App()
app.login()
app.mainloop()
