import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import sys
import time
import firebase_admin
from firebase_admin import credentials, db
import threading
import os
import sys
import atexit
import gspread
from google.oauth2.service_account import Credentials
from cryptography.fernet import Fernet
import json

VERSION = "1.04.01"
REPO_OWNER = "eingelc"

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
elif 'ipykernel' in sys.modules:
    BASE_DIR = os.getcwd()
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = os.path.join(BASE_DIR, "Files")

if not os.path.exists(FILES_DIR):
    os.makedirs(FILES_DIR)

key_path = os.path.join(FILES_DIR, "secret.key")
enc_path = os.path.join(FILES_DIR, "arcbest.enc")
arc_json = os.path.join(FILES_DIR,"arcbest.json")

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

Issues_Dict = {
    "RFM": ["Worklist issue", "Load issue", "DBW issue", "Vehicle disconnection", "No available connection"],
    "Unknown": ["Network issue", "Local conditions", "Site emergency", "Manual operator", "Power cycle", "Other"],
    "Vaux Drive": ["Audio issue", "Camera issue", "PTZ issue", "High Latency", "OP station issue", "Teleop command", "Reset not pressed"],
    "Vehicle": ["Lidar issue", "Low battery", "Calibration issue", "Throttle loss", "Pallet issue", "Mislocated issue", "Protective stop"]
}

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
with open(key_path, "rb") as f:
    key = f.read()
fernet = Fernet(key)
with open(enc_path, "rb") as f:
    encrypted_data = f.read()
decrypted_data = fernet.decrypt(encrypted_data)
google_creds = json.loads(decrypted_data.decode())
Google_Credentials_Loaded = Credentials.from_service_account_info(info=google_creds, scopes=SCOPES)
gc = gspread.authorize(Google_Credentials_Loaded)
sh1 = gc.open_by_key("ajiwjdoiwjadoaj1239vsjdse")
worksheet = sh1.worksheet("RAW_EVENTS")
print("Google cargado correctamente...")

class App(ctk.CTk):
    def __init__(self):
        #App
        print("Iniciando interfaz...")
        super().__init__()
        self.geometry(f"{1000}x{420}")
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=1)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.resizable(False, False)
        #atexit.register(self.on_close)
        self.usuario_seleccionado = None
        self.site_seleccionado = None
        self.vehiculo_seleccionado = None
        self.log_completo = "Esperando Actividad..."
        self.pilotos_widgets = {}
        self.botones_vehiculos = {}
        self.botones_issues = {}
        self.cache_issues = []
        self.logs_DF = []
        self.vehiculo_bool = False

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
        self.frame_palete.grid(row=0, column=1, rowspan=6, sticky="nsew")
        self.frame_palete.grid_columnconfigure(0, weight=1)
        self.frame_palete.grid_columnconfigure(1, weight=1)
        #self.frame_palete.grid_rowconfigure(1, weight=1)

        self.pallet_label = ctk.CTkLabel(self.frame_palete, text="Palletes", font=ctk.CTkFont(size=16, weight="bold"))
        self.pallet_label.grid(row=0, column=0, columnspan=2, padx=(20), pady=(0, 5), sticky="ew")
 
        self.pallet_add = ctk.CTkButton(self.frame_palete, text="Agregar Pallete", state="disabled", command=lambda: self.actualizar_palletes(int(1)))
        self.pallet_add.grid(row=1, column=0, padx=(20, 10), pady=(10), sticky="nsew")
        self.pallet_remove = ctk.CTkButton(self.frame_palete, text="Eliminar Pallete", state="disabled", command=lambda: self.actualizar_palletes(int(-1)))
        self.pallet_remove.grid(row=1, column=1, padx=(10, 20), pady=(10), sticky="nsew")

        self.issue_label = ctk.CTkLabel(self.frame_palete, text="Issues", font=ctk.CTkFont(size=16, weight="bold"))
        self.issue_label.grid(row=2, column=0, columnspan=2, padx=(20), pady=(0, 5), sticky="ew")

        self.issue_segments = ctk.CTkSegmentedButton(self.frame_palete, values=list(Issues_Dict.keys()),state="disabled", command=self.mostrar_issues)
        self.issue_segments.grid(row=3, column=0, columnspan=2, padx=20, pady=(5, 10), sticky="ew")

        self.frame_issues = ctk.CTkFrame(self.frame_palete, width=200, height=100, fg_color="transparent")
        self.frame_issues.grid(row=4, column=0, columnspan=2, sticky="nsew")

        self.issue_label = ctk.CTkLabel(self.frame_palete, text="Vehiculos", font=ctk.CTkFont(size=16, weight="bold"))
        self.issue_label.grid(row=5, column=0, columnspan=2, padx=(20), pady=(0, 5), sticky="ew")

        self.frame_vehiculos = ctk.CTkFrame(self.frame_palete, width=200, height=100, fg_color="transparent")
        self.frame_vehiculos.grid(row=6, column=0, columnspan=2, sticky="nsew")

        #Seccion 2 B
        self.frame_palete1 = ctk.CTkFrame(self, width=300, fg_color="transparent")
        self.frame_palete1.grid_rowconfigure(1, weight=1)
        self.frame_palete1.grid(row=0, column=2, rowspan=5, sticky="nsew")
        self.frame_palete1.grid_columnconfigure(0, weight=1)
        self.frame_palete1.grid_propagate(False)
        self.log_text = ctk.CTkTextbox(self.frame_palete1, width=200, font=ctk.CTkFont(size=11), activate_scrollbars=True, wrap="word")
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.log_text.insert("0.0", self.log_completo)
        self.log_text.configure(state="disabled")

        self.opened_issues_frame = ctk.CTkScrollableFrame(self.frame_palete1, label_text="Opened Issues")
        self.opened_issues_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

    def iniciar_listener(self):
        def callback(event):
            usuarios = db.reference("/usuarios/").get()
            if self.winfo_exists() and usuarios:
                self.after(0, lambda: self.mostrar_pilotos_activos(usuarios))
        self.usuarios_listener = db.reference('usuarios').listen(callback)

    def mostrar_issues(self, seleccion):
        for widget in self.frame_issues.winfo_children():
            widget.destroy()
        self.botones_issues = {}
        issues = Issues_Dict.get(seleccion, [])

        for n in range(4):
            self.frame_issues.grid_columnconfigure(n, weight=1)

        for i, nombre_issue in enumerate(issues):
            fila = i // 4
            columna = i % 4
            btn = ctk.CTkButton(self.frame_issues, text=nombre_issue, fg_color="#4A4A4A", hover_color="#666666", height=40)
            btn.configure(command=lambda b=btn, v=nombre_issue: self.seleccionar_issue(v, b))
            btn.grid(row=fila, column=columna, padx=5, pady=5, sticky="nsew") 
            self.botones_issues[nombre_issue] = btn

    def seleccionar_issue(self, issue, boton_original):
        ahora = time.strftime("%H:%M:%S")
        COLOR_ROJO = "#FF4B4B"
        boton_original.configure(fg_color=COLOR_ROJO, hover_color="#B22222")
        fila_reporte = ctk.CTkFrame(self.opened_issues_frame, fg_color="gray25")
        fila_reporte.pack(pady=2, fill="x", padx=5)
        lbl_info = ctk.CTkLabel(fila_reporte, text=f"[{ahora}] {issue}", font=ctk.CTkFont(size=11))
        lbl_info.pack(side="left", padx=10, pady=5)
        btn_resolver = ctk.CTkButton(fila_reporte, text="Resuelto", width=60, height=20, fg_color="#2fa572", hover_color="#1e6e4c")
        btn_resolver.pack(side="right", padx=5, pady=5)

        reporte = {"nombre": issue, "contenedor": fila_reporte, "referencia_original": boton_original}
        btn_resolver.configure(command=lambda r=reporte: self.eliminar_reporte(r))
        self.cache_issues.append(reporte)
        self.agregar_log(Mode="Issue", Event="Issue Started")

    def eliminar_reporte(self, reporte_dict):
        reporte_dict["contenedor"].destroy()
        if reporte_dict in self.cache_issues:
            self.cache_issues.remove(reporte_dict)

        nombre_issue = reporte_dict["nombre"]
        quedan_otros = any(r["nombre"] == nombre_issue for r in self.cache_issues)
        
        if not quedan_otros:
            try:
                reporte_dict["referencia_original"].configure(fg_color="#4A4A4A", hover_color="#666666")
            except:
                pass
        self.agregar_log(Mode="Issue", Event="Issue Ended")

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
            btn = ctk.CTkButton(self.frame_vehiculos, text=nombre_vehiculo, fg_color="#3a3a3a")
            btn.configure(command=lambda b=btn, v=nombre_vehiculo: self.seleccionar_vehiculo(v, b))
            btn.grid(row=fila, column=columna, padx=5, pady=5, sticky="nsew")
            self.botones_vehiculos[nombre_vehiculo] = btn
        self.iniciar_listener_vehiculos(sitio_actual)

    def iniciar_listener_vehiculos(self, sitio):
        def callback(event):
            datos_sitio = db.reference(f'sitios/{sitio}').get()
            if datos_sitio:
                self.after(0, lambda: self.actualizar_colores_tiempo_real(datos_sitio))
        self.vehiculos_listener = db.reference(f'sitios/{sitio}').listen(callback)

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
                    btn.configure(fg_color=COLOR_OCUPADO, state="disabled", text=f"{nombre_v}\n({usuario_que_lo_tiene})")
                elif status == "online" and usuario_que_lo_tiene == self.usuario_seleccionado:
                    btn.configure(fg_color=COLOR_MIO, state="normal", text=f"{nombre_v}\n(Tú)")
                elif self.vehiculo_bool == True:
                    btn.configure(fg_color=COLOR_NORMAL, state="disabled", text=nombre_v)
                else:
                    btn.configure(fg_color=COLOR_NORMAL, state="normal", text=nombre_v)

                if self.cronometro_activo == False:
                    btn.configure(state="disabled")

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
        if actual.get("status") == "offline":
            ref.update({
                "status": "online",
                "user": self.usuario_seleccionado
            })
            self.vehiculo_seleccionado = nombre_v
            self.agregar_log(Mode="Working", Event="Vehicle Selected")
            self.vehiculo_bool = True
            self.btn_turno.configure(state="disabled")
            self.activar_opciones(estado="normal")
        else:
            ref.update({
                "status": "offline",
                "user": "none"
            })
            self.vehiculo_seleccionado = None
            self.agregar_log(Mode="Working", Event="Vehicle Deselected")
            self.vehiculo_bool = False
            self.btn_turno.configure(state="normal")
            self.activar_opciones(estado="disabled")

    def agregar_log(self, Mode, Event):
        ahora = time.strftime("%H:%M:%S")
        hoy = time.strftime("%d/%m/%Y %H:%M:%S")
        self.logs_DF.append([hoy, self.site_seleccionado, self.usuario_seleccionado, self.vehiculo_seleccionado, Mode, Event])
        mensaje = f"{Event} at {ahora} | {self.site_seleccionado} | {self.usuario_seleccionado}"

        self.log_text.configure(state="normal")
        formato_mensaje = f"\n> {mensaje}"
        self.log_text.insert("end", formato_mensaje)
        self.log_completo += formato_mensaje
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def actualizar_palletes(self, count):
        self.pallet_count = self.pallet_count + count
        if self.pallet_count >= 0:
            if count > 0:
                Evento = "Pallet_Added"
            else:
                Evento = "Pallet_Deleted"
            self.pallet_label.configure(text=f"Palletes: {self.pallet_count}")
            self.agregar_log(Mode="Working", Event=Evento)
        else:
            self.pallet_count = 0

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
            #self.wait_window(self.login_window)

    def cambiar_sesion(self):
        respuesta = messagebox.askokcancel(title="Cambiar Sesión", message="¿Estás seguro de que deseas cambiar de sesión? Esto reiniciará el cronómetro y el conteo de palletes.", parent=self, icon="warning")
        if respuesta:
            self.agregar_log(Mode="Waiting", Event="Logout")
            self.cambiar_estatus_firebase("offline")
            self.upload_data()
            self.mostrar_pilotos_activos(db.reference("/usuarios/").get())
            self.usuario_seleccionado = None
            self.site_seleccionado = None
            self.cronometro_activo = False
            self.pallet_count = 0
            self.label_tiempo.configure(text="00:00:00")
            self.pallet_label.configure(text="Palletes: 0")
            self.btn_turno.configure(text="Iniciar Turno", fg_color="green")
            self.vehiculo_seleccionado = None
            self.log_completo = "Esperando Actividad..."
            self.pilotos_widgets = {}
            self.botones_vehiculos = {}
            self.botones_issues = {}
            self.cache_issues = []
            self.logs_DF = []
            self.vehiculo_bool = False
            self.login()

    def finalizar_login(self):
        self.usuario_seleccionado = self.Usuario.get()
        self.site_seleccionado = self.Site.get()

        if self.usuario_seleccionado == "Piloto" or self.site_seleccionado == "Sitio":
            messagebox.showerror("Error", "Por favor, seleccione un piloto y un sitio válidos.", parent=self.login_window, icon="error")
        else:
            self.agregar_log(Mode="Waiting", Event="Login")
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

    def activar_opciones(self, estado):
        self.issue_segments.configure(state=estado)
        self.pallet_add.configure(state=estado)
        self.pallet_remove.configure(state=estado)
        for issue in self.botones_issues:
            btn = self.botones_issues[issue]
            btn.configure(state=estado)

    def cambiar_botones(self, estado):
        sitio = self.site_seleccionado
        datos_sitio = db.reference(f'sitios/{sitio}').get()
        for nombre_v, info in datos_sitio.items():
            status = info.get("status", "offline")
            btn = self.botones_vehiculos[nombre_v]
            if status == "online":
                btn.configure(state="disabled")
            else:
                btn.configure(state=estado)

    def gestionar_turno(self):
        if self.cronometro_activo == False:
            self.agregar_log(Mode="Waiting", Event="Shift Started")
            self.inicio_turno = time.time()
            self.cronometro_activo = True
            self.btn_turno.configure(text="Finalizar Turno", fg_color="red")
            self.actualizar_cronometro()
            self.cambiar_botones(estado="normal")
        else:
            self.agregar_log(Mode="Waiting", Event="Shift Ended")
            self.cronometro_activo = False
            self.btn_turno.configure(text="Iniciar Turno", fg_color="green")
            self.cambiar_botones(estado="disabled")

    def actualizar_cronometro(self):
        if self.cronometro_activo:
            tiempo_actual = time.time() - self.inicio_turno
            horas = int(tiempo_actual // 3600)
            minutos = int((tiempo_actual % 3600) // 60)
            segundos = int(tiempo_actual % 60)
            self.label_tiempo.configure(text=f"{horas:02d}:{minutos:02d}:{segundos:02d}")
            self.after(1000, self.actualizar_cronometro)

    def on_close(self):
        print("Iniciando cierre seguro...")
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        def proceso_final():
            try:
                print("Subiendo datos a Google Sheets...")
                self.upload_data()
                print("Cerrando sesión en Firebase...")
                self.cambiar_estatus_firebase("offline")
                '''
                if hasattr(self, 'usuarios_listener'):
                    self.usuarios_listener.close()
                if hasattr(self, 'vehiculos_listener'):
                    self.vehiculos_listener.close()
                '''
            except Exception as e:
                print(f"Error durante el cierre: {e}")
            finally:
                self.after(0, self.destruccion_final)

        thread_cierre = threading.Thread(target=proceso_final)
        thread_cierre.start()

    def destruccion_final(self):
        print("App destruida con éxito.")
        self.quit()
        self.destroy()
        os._exit(0)

    def upload_data(self):
        worksheet.append_rows(self.logs_DF)
        print("Data subida con éxito")

if __name__ == "__main__":
    app = App()
    app.title("ArcBest Register")
    app.login()
    app.mainloop()
