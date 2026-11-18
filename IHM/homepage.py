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

class HomePage:
    """Page d'accueil pour choisir le mode d'utilisation"""
    def __init__(self, parent, on_live_mode, on_csv_mode):
        self.parent = parent
        self.on_live_mode = on_live_mode
        self.on_csv_mode = on_csv_mode
        self.create_ui()
    
    def create_ui(self):
        # Frame principal avec fond clair
        self.main_frame = tk.Frame(self.parent, bg="#f5f5f5")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titre
        title_frame = tk.Frame(self.main_frame, bg="#f5f5f5")
        title_frame.pack(pady=60)
        
        title = tk.Label(
            title_frame,
            text="Asservissement Moteur",
            font=("Arial", 28, "bold"),
            fg="#2c3e50",
            bg="#f5f5f5"
        )
        title.pack()
        
        subtitle = tk.Label(
            title_frame,
            text="Système de Contrôle et Visualisation",
            font=("Arial", 12),
            fg="#7f8c8d",
            bg="#f5f5f5"
        )
        subtitle.pack(pady=8)
        
        # Frame pour les boutons
        button_frame = tk.Frame(self.main_frame, bg="#f5f5f5")
        button_frame.pack(pady=40)
        
        # Bouton Lecture Temps Réel
        self.live_button = tk.Button(
            button_frame,
            text="Lecture Temps Réel",
            font=("Arial", 14),
            bg="#3498db",
            fg="white",
            activebackground="#2980b9",
            activeforeground="white",
            width=22,
            height=2,
            relief="flat",
            cursor="hand2",
            command=self.on_live_clicked
        )
        self.live_button.pack(pady=10)
        
        # Bouton Importer CSV
        self.csv_button = tk.Button(
            button_frame,
            text="Importer Fichier CSV",
            font=("Arial", 14),
            bg="#2ecc71",
            fg="white",
            activebackground="#27ae60",
            activeforeground="white",
            width=22,
            height=2,
            relief="flat",
            cursor="hand2",
            command=self.on_csv_clicked
        )
        self.csv_button.pack(pady=10)
    
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
