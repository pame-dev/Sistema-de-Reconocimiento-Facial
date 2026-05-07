# views/informacion_escolar/estilos.py
from tkinter import ttk
from views.font_scale import FontScale

ROL_COLOR = {"alumno": "#4A90D9", "maestro": "#27AE60", "personal": "#E67E22"}
ROL_ICONO = {"alumno": "🎓",      "maestro": "📚",      "personal": "🏢"}


class EstilosMixin:
    """
    Aplica estilos ttk (Treeview, Scrollbar, Combobox) con los colores del tema.
    Requiere: self.colors, self.parent.
    """

    def _aplicar_estilo_tabla(self):
        c = self.colors
        style = ttk.Style()
        style.theme_use('default')

        style.configure('Dark.Treeview',
            background=c['tree_bg'],
            fieldbackground=c['tree_bg'],
            foreground=c['tree_fg'],
            rowheight=32, borderwidth=0,
            font=FontScale.f(12),
        )
        style.configure('Dark.Treeview.Heading',
            background=c['tree_head_bg'],
            foreground=c['tree_head_fg'],
            font=FontScale.fb(12),
            relief='flat', padding=6,
        )
        style.map('Dark.Treeview',
            background=[('selected', c['tree_sel_bg'])],
            foreground=[('selected', c['tree_sel_fg'])],
        )
        style.map('Dark.Treeview.Heading',
            background=[('active', c['tree_head_bg'])],
        )
        style.configure('Dark.Vertical.TScrollbar',
            background=c['card_bg'], troughcolor=c['background'],
            arrowcolor=c['text_gray'], borderwidth=0)
        style.configure('Dark.Horizontal.TScrollbar',
            background=c['card_bg'], troughcolor=c['background'],
            arrowcolor=c['text_gray'], borderwidth=0)
        style.configure('Dark.TCombobox',
            fieldbackground=c['card_bg'], background=c['card_bg'],
            foreground=c['text_dark'], arrowcolor=c['text_gray'],
            bordercolor=c['border'], selectbackground=c['tree_sel_bg'],
            selectforeground=c['tree_sel_fg'],
        )
        style.map('Dark.TCombobox',
            fieldbackground=[('readonly', c['card_bg'])],
            foreground=[('readonly', c['text_dark'])],
            background=[('readonly', c['card_bg'])],
        )

        win = self.parent.winfo_toplevel()
        win.option_add("*TCombobox*Listbox.background",       c['card_bg'])
        win.option_add("*TCombobox*Listbox.foreground",       c['text_dark'])
        win.option_add("*TCombobox*Listbox.selectBackground", c['tree_sel_bg'])
        win.option_add("*TCombobox*Listbox.selectForeground", c['tree_sel_fg'])
        win.option_add("*TCombobox*Listbox.font",             ("Segoe UI", 13))