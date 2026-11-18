# coding: utf-8
import sys
major=sys.version_info.major
minor=sys.version_info.minor
if major==2 and minor==7 :
    import Tkinter as tk
elif major==3 :
    import tkinter as tk
else :
    import tkinter as tk

import theme

class HomePage:
    """Page d'accueil pour choisir le mode d'utilisation"""
    def __init__(self, parent, on_live_mode, on_csv_mode):
        self.parent = parent
        self.on_live_mode = on_live_mode
        self.on_csv_mode = on_csv_mode
        self.create_ui()

    def create_ui(self):
        # Frame principal
        self.main_frame = tk.Frame(self.parent, bg=theme.BG, width=900, height=600)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Carte centrale
        card = tk.Frame(
            self.main_frame,
            bg=theme.SURFACE,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            padx=60,
            pady=40,
        )
        card.place(relx=0.5, rely=0.5, anchor="center")

        # Bandeau d'accent
        tk.Frame(card, bg=theme.ACCENT, height=4, width=80).pack(pady=(0, 24))

        # Titre
        title = tk.Label(
            card,
            text="Asservissement Moteur",
            font=theme.FONT_TITLE,
            fg=theme.TEXT,
            bg=theme.SURFACE
        )
        title.pack()

        subtitle = tk.Label(
            card,
            text="Système de Contrôle et Visualisation",
            font=theme.FONT_SUBTITLE,
            fg=theme.MUTED,
            bg=theme.SURFACE
        )
        subtitle.pack(pady=(6, 30))

        # Frame pour les boutons
        button_frame = tk.Frame(card, bg=theme.SURFACE)
        button_frame.pack()

        # Bouton Lecture Temps Réel
        self.live_button = tk.Button(
            button_frame,
            text="▶  Lecture Temps Réel",
            font=(theme.FONT_FAMILY, 13, "bold"),
            bg=theme.ACCENT,
            fg="white",
            activebackground=theme.ACCENT_ACTIVE,
            activeforeground="white",
            width=24,
            pady=10,
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.on_live_clicked
        )
        self.live_button.pack(pady=8)

        # Bouton Importer CSV
        self.csv_button = tk.Button(
            button_frame,
            text="Importer Fichier CSV",
            font=(theme.FONT_FAMILY, 13, "bold"),
            bg=theme.SURFACE_2,
            fg=theme.TEXT,
            activebackground=theme.BORDER,
            activeforeground="white",
            width=24,
            pady=10,
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.on_csv_clicked
        )
        self.csv_button.pack(pady=8)

        # Pied de page
        tk.Label(
            card,
            text="ENIB · S7 · ACE — Projet 5",
            font=theme.FONT_SMALL,
            fg=theme.MUTED,
            bg=theme.SURFACE
        ).pack(pady=(28, 0))

    def on_live_clicked(self):
        """Callback pour le mode temps réel"""
        self.on_live_mode()

    def on_csv_clicked(self):
        """Callback pour le mode CSV"""
        self.on_csv_mode()

    def destroy(self):
        """Détruire la page d'accueil"""
        if hasattr(self, 'main_frame'):
            self.main_frame.destroy()


if __name__ == "__main__":
    def test_live():
        print("Mode Live sélectionné")

    def test_csv():
        print("Mode CSV sélectionné")

    root = tk.Tk()
    root.title("Test HomePage")
    root.geometry("800x600")

    homepage = HomePage(root, test_live, test_csv)

    root.mainloop()
