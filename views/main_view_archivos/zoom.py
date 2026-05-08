import tkinter as tk
from config import COLORS
from views.font_scale import FontScale

ZOOM_MIN  = 0.7
ZOOM_MAX  = 2.0
ZOOM_STEP = 0.1


class ZoomMixin:
    def _capturar_base_real_ventana(self):
        """Guarda el tamaño real inicial de la ventana como base de escalado."""
        try:
            root = self.parent.winfo_toplevel()
            root.update_idletasks()
            w = root.winfo_width()
            h = root.winfo_height()
            if w > 200 and h > 150:
                self._base_w = w
                self._base_h = h
        except Exception:
            pass

    def _bind_zoom_keys(self):
        root = self.parent.winfo_toplevel()

        def zoom_in(event):
            self._zoom(ZOOM_STEP)
            return "break"

        def zoom_out(event):
            self._zoom(-ZOOM_STEP)
            return "break"

        def zoom_reset(event):
            self._zoom_reset()
            return "break"

        root.bind_all("<Control-plus>",        zoom_in)
        root.bind_all("<Control-equal>",       zoom_in)
        root.bind_all("<Control-Shift-equal>", zoom_in)
        root.bind_all("<Control-KP_Add>",      zoom_in)
        root.bind_all("<Control-minus>",       zoom_out)
        root.bind_all("<Control-KP_Subtract>", zoom_out)
        root.bind_all("<Control-0>",           zoom_reset)
        root.bind_all("<Control-KP_0>",        zoom_reset)

    def _zoom(self, delta):
        nueva = round(FontScale.get() + delta, 2)
        if not (ZOOM_MIN <= nueva <= ZOOM_MAX):
            return
        FontScale.set(nueva)
        self._zoom_manual = True
        self._actualizar_btn_zoom()
        self._recargar_vista()
        self._cerrar_popover()

    def _zoom_reset(self):
        if FontScale.get() == 1.0:
            return
        FontScale.set(1.0)
        self._zoom_manual = True
        self._actualizar_btn_zoom()
        self._recargar_vista()
        self._cerrar_popover()

    def _actualizar_btn_zoom(self):
        pct = round(FontScale.get() * 100)
        try:
            self._btn_zoom.configure(text=f"🔍 {pct}%")
        except Exception:
            pass
        if self._zoom_popover and self._zoom_popover.winfo_exists():
            try:
                self._zoom_slider.set(pct)
                self._zoom_pct_lbl.configure(text=f"{pct}%")
            except Exception:
                pass

    def _recargar_vista(self):
        self._guardar_estado_vista_actual()
        vistas = {
            "home":             self.show_home,
            "nuevo_registro":   self.show_nuevo_registro,
            "info_escolar":     self.show_informacion_escolar,
            "historial":        self.show_historial_accesos,
            "pantalla_accesos": self.show_pantalla_accesos,
        }
        vistas.get(self._vista_actual, self.show_home)()

    def _on_root_configure(self, event):
        try:
            if self._zoom_manual:
                # Si el usuario ya ajustó manualmente el zoom, no sobreescribirlo
                try:
                    pct = round(FontScale.get() * 100)
                    if hasattr(self, '_btn_zoom'):
                        self._btn_zoom.configure(text=f"🔍 {pct}%")
                except Exception:
                    pass
                if self._vista_actual == "pantalla_accesos":
                    self._sincronizar_layout_pantalla_accesos()
                return

            # Base design for scaling (use app start size if available)
            base_w, base_h = self._base_w, self._base_h
            w = max(320, event.width)
            h = max(240, event.height)
            scale_w = w / base_w
            scale_h = h / base_h
            scale = min(max(scale_w, 0.7), max(scale_h, 0.7))

            # Keep readability stable: automatic scaling should not go below 100%.
            # Users can still reduce manually from the zoom control when needed.
            scale = max(1.0, min(1.5, scale))

            # Evita bucle de repintado continuo por eventos Configure.
            if self._last_scale is not None and abs(scale - self._last_scale) < 0.01:
                return

            self._last_scale = scale
            FontScale.set(scale)

            # Adjust sidebar width proportionally
            try:
                new_sidebar = int(250 * scale)
                if hasattr(self, 'sidebar') and self.sidebar.winfo_exists():
                    self.sidebar.configure(width=new_sidebar)
            except Exception:
                pass

            # Update zoom button text
            try:
                pct = round(FontScale.get() * 100)
                if hasattr(self, '_btn_zoom'):
                    self._btn_zoom.configure(text=f"🔍 {pct}%")
            except Exception:
                pass

            if self._vista_actual == "pantalla_accesos":
                self._sincronizar_layout_pantalla_accesos()

        except Exception:
            pass

    def _esta_en_pantalla_completa(self):
        root = self.parent.winfo_toplevel()
        try:
            if bool(root.attributes("-fullscreen")):
                return True
        except Exception:
            pass
        try:
            if str(root.state()).lower() == "zoomed":
                return True
        except Exception:
            pass
        try:
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            w = root.winfo_width()
            h = root.winfo_height()
            return w >= sw - 20 and h >= sh - 20
        except Exception:
            return False

    def _debe_usar_layout_vertical_accesos(self):
        return not self._esta_en_pantalla_completa()

    def _sincronizar_layout_pantalla_accesos(self):
        vertical = self._debe_usar_layout_vertical_accesos()
        if self._accesos_layout_vertical is None or vertical != self._accesos_layout_vertical:
            self._aplicar_layout_pantalla_accesos(vertical)

    def _aplicar_layout_pantalla_accesos(self, vertical=True):
        body = getattr(self, "_accesos_body", None)
        if not body or not body.winfo_exists():
            return

        try:
            self._cam_card.grid_forget()
            self._user_card.grid_forget()
        except Exception:
            pass

        # Limpiar configuraciones previas de grid.
        for idx in (0, 1):
            try:
                body.grid_rowconfigure(idx, weight=0, minsize=0)
            except Exception:
                pass
            try:
                body.grid_columnconfigure(idx, weight=0, minsize=0)
            except Exception:
                pass

        if vertical:
            body.grid_rowconfigure(0, weight=4, minsize=360)
            body.grid_rowconfigure(1, weight=1, minsize=170)
            body.grid_columnconfigure(0, weight=1)

            self._cam_card.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
            self._user_card.grid(row=1, column=0, sticky="nsew")
        else:
            body.grid_rowconfigure(0, weight=1)
            body.grid_columnconfigure(0, weight=3)
            body.grid_columnconfigure(1, weight=2)

            self._cam_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
            self._user_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self._accesos_layout_vertical = vertical

    def _guardar_estado_vista_actual(self):
        if self._vista_actual != "nuevo_registro":
            return
        vista = getattr(self, "_nuevo_registro_view", None)
        if not vista:
            return
        try:
            self._nuevo_registro_state = vista.export_state()
        except Exception:
            self._nuevo_registro_state = None

    # ── Popover zoom ──────────────────────────────────────────────────────────
    def _toggle_zoom_popover(self):
        if self._zoom_popover and self._zoom_popover.winfo_exists():
            self._cerrar_popover()
            return

        btn = self._btn_zoom
        x   = btn.winfo_rootx()
        y   = btn.winfo_rooty() + btn.winfo_height() + 6

        pop = tk.Toplevel(self.main_frame)
        pop.overrideredirect(True)
        pop.geometry(f"250x160+{x}+{y}")
        pop.configure(bg="#1e3a5f")
        pop.attributes("-topmost", True)
        self._zoom_popover = pop
        pop.bind("<Escape>", lambda e: self._cerrar_popover())
        pop.focus_force()

        inner = tk.Frame(pop, bg="#1e3a5f")
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        header_row = tk.Frame(inner, bg="#1e3a5f")
        header_row.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(header_row, text="Zoom", bg="#1e3a5f", fg="#93c5fd",
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Button(header_row, text="✕", bg="#1e3a5f", fg="#ffffff", relief="flat",
                  activebackground="#2563eb", activeforeground="white",
                  font=("Segoe UI", 10, "bold"), bd=0, padx=4, pady=0,
                  command=self._cerrar_popover, takefocus=0).pack(side="right")

        self._zoom_pct_lbl = tk.Label(inner, text=f"{round(FontScale.get()*100)}%",
            bg="#1e3a5f", fg="#ffffff", font=("Segoe UI", 26, "bold"))
        self._zoom_pct_lbl.pack(pady=(0, 6))

        self._zoom_slider = tk.Scale(inner,
            from_=int(ZOOM_MIN*100), to=int(ZOOM_MAX*100),
            orient="horizontal", resolution=10,
            bg="#1e3a5f", fg="#93c5fd", troughcolor="#1d4ed8",
            highlightthickness=0, bd=0, sliderrelief="flat",
            activebackground="#60a5fa", length=220, showvalue=False, takefocus=0,
            command=self._zoom_desde_slider)
        current_pct = round(FontScale.get() * 100)
        self._zoom_slider.set(current_pct)
        self._zoom_slider.pack(padx=12, pady=(2, 10))

    def _cerrar_popover(self):
        try:
            if self._zoom_popover and self._zoom_popover.winfo_exists():
                self._zoom_popover.destroy()
        except Exception:
            pass
        self._zoom_popover = None

    def _zoom_desde_slider(self, val):
        try:
            nueva = round(float(val) / 100, 2)
        except Exception:
            return
        if nueva == FontScale.get():
            return
        FontScale.set(nueva)
        self._zoom_manual = True
        pct = round(FontScale.get() * 100)
        try:
            self._zoom_pct_lbl.configure(text=f"{pct}%")
            self._btn_zoom.configure(text=f"🔍 {pct}%")
        except Exception:
            pass
        if hasattr(self, "_slider_job"):
            try:
                self.main_frame.after_cancel(self._slider_job)
            except Exception:
                pass
        self._slider_job = self.main_frame.after(300, self._recargar_vista)